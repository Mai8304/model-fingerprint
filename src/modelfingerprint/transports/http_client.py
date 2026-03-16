from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from time import monotonic
from typing import Any, Protocol

import httpx

from modelfingerprint.dialects.base import HttpRequestSpec


@dataclass(eq=False)
class HttpClientError(Exception):
    kind: str
    message: str
    status_code: int | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)


@dataclass(frozen=True)
class HttpProgressSnapshot:
    bytes_received: int
    has_any_data: bool
    elapsed_ms: int
    first_byte_latency_ms: int | None = None
    last_progress_latency_ms: int | None = None
    completed: bool = False
    terminal_error_kind: str | None = None


@dataclass(frozen=True)
class HttpTerminalResult:
    payload: dict[str, object] | None
    latency_ms: int | None
    error: HttpClientError | None


@dataclass(frozen=True)
class HttpRequestTimeouts:
    connect_seconds: float
    first_byte_seconds: float
    idle_seconds: float
    total_seconds: float


class HttpClient(Protocol):
    def send(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> tuple[dict[str, object], int]: ...


class InFlightHttpRequest(Protocol):
    def snapshot(self) -> HttpProgressSnapshot: ...

    def wait_until_terminal(
        self,
        timeout_seconds: float | None = None,
    ) -> HttpTerminalResult | None:
        ...

    def cancel(self) -> None: ...


class StandardHttpClient:
    def __init__(
        self,
        *,
        first_byte_timeout_seconds: float | None = None,
        idle_timeout_seconds: float | None = None,
        client_factory: Callable[..., httpx.AsyncClient] | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._first_byte_timeout_seconds = first_byte_timeout_seconds
        self._idle_timeout_seconds = idle_timeout_seconds
        self._client_factory = client_factory or httpx.AsyncClient
        self._clock = clock

    def send(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> tuple[dict[str, object], int]:
        handle = self.start(
            request,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
        )
        timeouts = self._resolve_timeouts(
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
        )
        terminal = handle.wait_until_terminal(
            timeout_seconds=timeouts.total_seconds + timeouts.connect_seconds + 1.0,
        )
        if terminal is None:
            handle.cancel()
            raise HttpClientError(
                kind="total_deadline_exceeded",
                message="request did not complete before the total deadline",
            )
        if terminal.error is not None:
            raise terminal.error
        assert terminal.payload is not None
        assert terminal.latency_ms is not None
        return terminal.payload, terminal.latency_ms

    def start(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> InFlightHttpRequest:
        return _StandardInFlightHttpRequest(
            request=request,
            timeouts=self._resolve_timeouts(
                connect_timeout_seconds=connect_timeout_seconds,
                read_timeout_seconds=read_timeout_seconds,
            ),
            client_factory=self._client_factory,
            clock=self._clock,
        )

    def _resolve_timeouts(
        self,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> HttpRequestTimeouts:
        total_seconds = float(read_timeout_seconds)
        first_byte_seconds = (
            total_seconds
            if self._first_byte_timeout_seconds is None
            else min(float(self._first_byte_timeout_seconds), total_seconds)
        )
        idle_seconds = (
            total_seconds
            if self._idle_timeout_seconds is None
            else min(float(self._idle_timeout_seconds), total_seconds)
        )
        return HttpRequestTimeouts(
            connect_seconds=float(connect_timeout_seconds),
            first_byte_seconds=max(first_byte_seconds, 0.001),
            idle_seconds=max(idle_seconds, 0.001),
            total_seconds=max(total_seconds, 0.001),
        )


class _StandardInFlightHttpRequest:
    def __init__(
        self,
        *,
        request: HttpRequestSpec,
        timeouts: HttpRequestTimeouts,
        client_factory: Callable[..., httpx.AsyncClient],
        clock: Callable[[], float],
    ) -> None:
        self._request = request
        self._timeouts = timeouts
        self._client_factory = client_factory
        self._clock = clock
        self._start_time = clock()
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._cancel = threading.Event()
        self._bytes_received = 0
        self._first_byte_latency_ms: int | None = None
        self._last_progress_latency_ms: int | None = None
        self._terminal_result: HttpTerminalResult | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[HttpTerminalResult] | None = None
        self._thread = threading.Thread(target=self._run, name="mf-http-inflight", daemon=True)
        self._thread.start()

    def snapshot(self) -> HttpProgressSnapshot:
        with self._lock:
            terminal_result = self._terminal_result
            bytes_received = self._bytes_received
            first_byte_latency_ms = self._first_byte_latency_ms
            last_progress_latency_ms = self._last_progress_latency_ms
        return HttpProgressSnapshot(
            bytes_received=bytes_received,
            has_any_data=bytes_received > 0,
            elapsed_ms=int((self._clock() - self._start_time) * 1000),
            first_byte_latency_ms=first_byte_latency_ms,
            last_progress_latency_ms=last_progress_latency_ms,
            completed=terminal_result is not None and terminal_result.error is None,
            terminal_error_kind=(
                None
                if terminal_result is None or terminal_result.error is None
                else terminal_result.error.kind
            ),
        )

    def wait_until_terminal(
        self,
        timeout_seconds: float | None = None,
    ) -> HttpTerminalResult | None:
        if not self._done.wait(timeout_seconds):
            return None
        with self._lock:
            return self._terminal_result

    def cancel(self) -> None:
        self._cancel.set()
        with self._lock:
            loop = self._loop
            task = self._task
        if loop is not None and task is not None and not task.done():
            loop.call_soon_threadsafe(task.cancel)

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self._lock:
            self._loop = loop
            self._task = loop.create_task(self._run_async())
            task = self._task
        assert task is not None
        try:
            terminal = loop.run_until_complete(task)
        finally:
            with self._lock:
                self._loop = None
                self._task = None
            loop.close()
        with self._lock:
            self._terminal_result = terminal
        self._done.set()

    async def _run_async(self) -> HttpTerminalResult:
        try:
            payload, latency_ms = await _perform_request_async(
                self._request,
                timeouts=self._timeouts,
                cancel_event=self._cancel,
                progress_callback=self._record_progress,
                client_factory=self._client_factory,
                clock=self._clock,
            )
            return HttpTerminalResult(payload=payload, latency_ms=latency_ms, error=None)
        except HttpClientError as exc:
            return HttpTerminalResult(payload=None, latency_ms=None, error=exc)
        except asyncio.CancelledError:
            return HttpTerminalResult(
                payload=None,
                latency_ms=None,
                error=HttpClientError(kind="cancelled", message="request cancelled"),
            )
        except Exception as exc:
            return HttpTerminalResult(
                payload=None,
                latency_ms=None,
                error=HttpClientError(
                    kind="transport_runtime_error",
                    message=str(exc) or "unexpected transport runtime error",
                ),
            )

    def _record_progress(self, chunk_size: int, *, elapsed_ms: int) -> None:
        with self._lock:
            self._bytes_received += chunk_size
            if self._first_byte_latency_ms is None:
                self._first_byte_latency_ms = elapsed_ms
            self._last_progress_latency_ms = elapsed_ms


async def _perform_request_async(
    request: HttpRequestSpec,
    *,
    timeouts: HttpRequestTimeouts,
    cancel_event: threading.Event | None,
    progress_callback: Callable[..., None] | None,
    client_factory: Callable[..., httpx.AsyncClient],
    clock: Callable[[], float],
) -> tuple[dict[str, object], int]:
    start_time = clock()
    total_deadline = start_time + timeouts.total_seconds
    first_byte_deadline = start_time + timeouts.first_byte_seconds
    client = client_factory(timeout=_build_httpx_timeout(timeouts))
    response_context = None
    response: Any = None

    try:
        _raise_if_cancelled(cancel_event)
        response_context = client.stream(
            "POST",
            request.url,
            headers=request.headers,
            json=request.body,
        )
        response = await _await_stream_open(
            response_context=response_context,
            cancel_event=cancel_event,
            clock=clock,
            first_byte_deadline=first_byte_deadline,
            total_deadline=total_deadline,
        )
        payload_bytes = await _read_response_body_async(
            response=response,
            cancel_event=cancel_event,
            clock=clock,
            first_byte_deadline=first_byte_deadline,
            total_deadline=total_deadline,
            idle_timeout_seconds=timeouts.idle_seconds,
            progress_callback=progress_callback,
            start_time=start_time,
        )
    except asyncio.CancelledError as exc:
        raise HttpClientError(kind="cancelled", message="request cancelled") from exc
    except httpx.ConnectTimeout as exc:
        raise HttpClientError(kind="connect_timeout", message="request connect timed out") from exc
    except httpx.HTTPError as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise HttpClientError(kind="cancelled", message="request cancelled") from exc
        raise HttpClientError(kind="network", message=str(exc)) from exc
    finally:
        if response_context is not None:
            await response_context.__aexit__(None, None, None)
        await client.aclose()

    latency_ms = int((clock() - start_time) * 1000)
    text = payload_bytes.decode("utf-8", errors="replace")
    status_code = _response_status(response)
    if status_code >= 400:
        message = text.strip() or _response_reason(response) or f"HTTP {status_code}"
        raise HttpClientError(
            kind="http_status",
            message=message,
            status_code=status_code,
        )

    payload = _decode_payload(
        request=request,
        response=response,
        text=text,
    )
    return payload, latency_ms


async def _await_stream_open(
    *,
    response_context: Any,
    cancel_event: threading.Event | None,
    clock: Callable[[], float],
    first_byte_deadline: float,
    total_deadline: float,
) -> Any:
    _raise_if_cancelled(cancel_event)
    timeout_seconds, timeout_kind = _next_wait_timeout(
        clock=clock,
        total_deadline=total_deadline,
        deadline=first_byte_deadline,
        timeout_kind="first_byte_timeout",
    )
    try:
        return await asyncio.wait_for(response_context.__aenter__(), timeout=timeout_seconds)
    except asyncio.TimeoutError as exc:
        raise _timeout_error(timeout_kind) from exc


async def _read_response_body_async(
    *,
    response: Any,
    cancel_event: threading.Event | None,
    clock: Callable[[], float],
    first_byte_deadline: float,
    total_deadline: float,
    idle_timeout_seconds: float,
    progress_callback: Callable[..., None] | None,
    start_time: float,
) -> bytes:
    chunks: list[bytes] = []
    iterator = response.aiter_bytes()
    first_chunk = True

    while True:
        _raise_if_cancelled(cancel_event)
        if first_chunk:
            timeout_seconds, timeout_kind = _next_wait_timeout(
                clock=clock,
                total_deadline=total_deadline,
                deadline=first_byte_deadline,
                timeout_kind="first_byte_timeout",
            )
        else:
            timeout_seconds, timeout_kind = _next_wait_timeout(
                clock=clock,
                total_deadline=total_deadline,
                duration_seconds=idle_timeout_seconds,
                timeout_kind="idle_timeout",
            )
        try:
            chunk = await asyncio.wait_for(anext(iterator), timeout=timeout_seconds)
        except StopAsyncIteration:
            break
        except asyncio.TimeoutError as exc:
            raise _timeout_error(timeout_kind) from exc
        if not chunk:
            continue
        chunks.append(chunk)
        first_chunk = False
        if progress_callback is not None:
            progress_callback(
                len(chunk),
                elapsed_ms=int((clock() - start_time) * 1000),
            )
    return b"".join(chunks)


def _next_wait_timeout(
    *,
    clock: Callable[[], float],
    total_deadline: float,
    timeout_kind: str,
    deadline: float | None = None,
    duration_seconds: float | None = None,
) -> tuple[float, str]:
    now = clock()
    remaining_total = total_deadline - now
    if remaining_total <= 0:
        raise _timeout_error("total_deadline_exceeded")
    if deadline is not None:
        remaining_stage = deadline - now
    else:
        assert duration_seconds is not None
        remaining_stage = duration_seconds
    if remaining_stage <= 0:
        raise _timeout_error(timeout_kind)
    if remaining_total <= remaining_stage:
        return remaining_total, "total_deadline_exceeded"
    return remaining_stage, timeout_kind


def _timeout_error(kind: str) -> HttpClientError:
    if kind == "connect_timeout":
        return HttpClientError(kind=kind, message="request connect timed out")
    if kind == "first_byte_timeout":
        return HttpClientError(
            kind=kind,
            message="response did not arrive before the first byte deadline",
        )
    if kind == "idle_timeout":
        return HttpClientError(
            kind=kind,
            message="response stream was idle past the idle timeout",
        )
    return HttpClientError(
        kind="total_deadline_exceeded",
        message="request did not complete before the total deadline",
    )


def _build_httpx_timeout(timeouts: HttpRequestTimeouts) -> httpx.Timeout:
    return httpx.Timeout(
        connect=timeouts.connect_seconds,
        read=None,
        write=timeouts.connect_seconds,
        pool=timeouts.connect_seconds,
    )


def _decode_payload(
    *,
    request: HttpRequestSpec,
    response: Any,
    text: str,
) -> dict[str, object]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, Mapping):
        return dict(payload)

    if _should_decode_sse(request=request, response=response):
        return _decode_sse_payload(text)

    if payload is not None:
        raise HttpClientError(
            kind="invalid_json",
            message="response body must be a JSON object",
        )
    raise HttpClientError(
        kind="invalid_json",
        message="response body is not valid JSON",
    )


def _should_decode_sse(*, request: HttpRequestSpec, response: Any) -> bool:
    accept = str(request.headers.get("Accept", "")).lower()
    if "text/event-stream" in accept:
        return True
    if request.body.get("stream") is True:
        return True
    content_type = _response_content_type(response).lower()
    return "text/event-stream" in content_type


def _response_content_type(response: Any) -> str:
    headers = getattr(response, "headers", None)
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if str(key).lower() == "content-type" and isinstance(value, str):
                return value
    return ""


def _response_status(response: Any) -> int:
    status_code = getattr(response, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    status = getattr(response, "status", None)
    if isinstance(status, int):
        return status
    return 0


def _response_reason(response: Any) -> str:
    reason_phrase = getattr(response, "reason_phrase", None)
    if isinstance(reason_phrase, str):
        return reason_phrase
    reason = getattr(response, "reason", None)
    if isinstance(reason, str):
        return reason
    return ""


def _decode_sse_payload(text: str) -> dict[str, object]:
    events = _parse_sse_events(text)
    if not events:
        raise HttpClientError(
            kind="invalid_json",
            message="response body is not valid JSON",
        )

    choices: dict[int, dict[str, object]] = {}
    usage: dict[str, object] | None = None

    for event in events:
        usage_payload = event.get("usage")
        if isinstance(usage_payload, Mapping):
            usage = dict(usage_payload)

        event_choices = event.get("choices")
        if not isinstance(event_choices, list):
            continue
        for raw_choice in event_choices:
            if not isinstance(raw_choice, Mapping):
                continue
            index = raw_choice.get("index", 0)
            if not isinstance(index, int):
                index = 0
            choice_state = choices.setdefault(
                index,
                {
                    "index": index,
                    "finish_reason": None,
                    "message": {},
                },
            )
            _merge_choice_delta(choice_state, raw_choice)

    if not choices and usage is None:
        raise HttpClientError(
            kind="invalid_json",
            message="response body is not valid JSON",
        )

    payload: dict[str, object] = {
        "choices": [choices[index] for index in sorted(choices)],
    }
    if usage is not None:
        payload["usage"] = usage
    return payload


def _parse_sse_events(text: str) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    data_lines: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if line == "":
            _flush_sse_event(data_lines, events)
            data_lines = []
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    _flush_sse_event(data_lines, events)
    return events


def _flush_sse_event(
    data_lines: list[str],
    events: list[dict[str, object]],
) -> None:
    if not data_lines:
        return
    data = "\n".join(data_lines).strip()
    if not data or data == "[DONE]":
        return
    try:
        payload = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HttpClientError(
            kind="invalid_json",
            message="response body is not valid JSON",
        ) from exc
    if not isinstance(payload, Mapping):
        raise HttpClientError(
            kind="invalid_json",
            message="response body must be a JSON object",
        )
    events.append(dict(payload))


def _merge_choice_delta(choice_state: dict[str, object], raw_choice: Mapping[str, object]) -> None:
    if raw_choice.get("finish_reason") is not None:
        choice_state["finish_reason"] = raw_choice.get("finish_reason")

    message = choice_state.setdefault("message", {})
    assert isinstance(message, dict)

    raw_message = raw_choice.get("message")
    if isinstance(raw_message, Mapping):
        _merge_message_payload(message, raw_message)

    delta = raw_choice.get("delta")
    if isinstance(delta, Mapping):
        _merge_message_payload(message, delta)


def _merge_message_payload(message: dict[str, object], payload: Mapping[str, object]) -> None:
    for key in ("content", "reasoning", "reasoning_content", "thinking"):
        value = payload.get(key)
        if isinstance(value, str) and value != "":
            existing = message.get(key)
            if isinstance(existing, str) and existing != "":
                message[key] = existing + value
            else:
                message[key] = value


def _raise_if_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise HttpClientError(kind="cancelled", message="request cancelled")
