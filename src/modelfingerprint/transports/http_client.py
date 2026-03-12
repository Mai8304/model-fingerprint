from __future__ import annotations

import json
import select
import ssl
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPSConnection
from time import monotonic
from typing import Any, Protocol
from urllib.parse import urlsplit

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
    def send(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> tuple[dict[str, object], int]:
        return _perform_request(
            request,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
        )

    def start(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> InFlightHttpRequest:
        return _StandardInFlightHttpRequest(
            request=request,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
        )


class _StandardInFlightHttpRequest:
    def __init__(
        self,
        *,
        request: HttpRequestSpec,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> None:
        self._request = request
        self._connect_timeout_seconds = connect_timeout_seconds
        self._read_timeout_seconds = read_timeout_seconds
        self._start_time = monotonic()
        self._lock = threading.Lock()
        self._done = threading.Event()
        self._cancel = threading.Event()
        self._connection: HTTPConnection | HTTPSConnection | None = None
        self._bytes_received = 0
        self._first_byte_latency_ms: int | None = None
        self._last_progress_latency_ms: int | None = None
        self._terminal_result: HttpTerminalResult | None = None
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
            elapsed_ms=int((monotonic() - self._start_time) * 1000),
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
            connection = self._connection
        if connection is not None:
            try:
                connection.close()
            except OSError:
                return

    def _run(self) -> None:
        try:
            payload, latency_ms = _perform_request(
                self._request,
                connect_timeout_seconds=self._connect_timeout_seconds,
                read_timeout_seconds=self._read_timeout_seconds,
                cancel_event=self._cancel,
                register_connection=self._register_connection,
                progress_callback=self._record_progress,
            )
            terminal = HttpTerminalResult(payload=payload, latency_ms=latency_ms, error=None)
        except HttpClientError as exc:
            terminal = HttpTerminalResult(payload=None, latency_ms=None, error=exc)
        except Exception as exc:
            terminal = HttpTerminalResult(
                payload=None,
                latency_ms=None,
                error=HttpClientError(
                    kind="transport_runtime_error",
                    message=str(exc) or "unexpected transport runtime error",
                ),
            )
        with self._lock:
            self._terminal_result = terminal
            self._connection = None
        self._done.set()

    def _register_connection(self, connection: HTTPConnection | HTTPSConnection | None) -> None:
        with self._lock:
            self._connection = connection

    def _record_progress(self, chunk_size: int, *, elapsed_ms: int) -> None:
        with self._lock:
            self._bytes_received += chunk_size
            if self._first_byte_latency_ms is None:
                self._first_byte_latency_ms = elapsed_ms
            self._last_progress_latency_ms = elapsed_ms


class _RequestCancelled(Exception):
    pass


def _perform_request(
    request: HttpRequestSpec,
    *,
    connect_timeout_seconds: int,
    read_timeout_seconds: int,
    cancel_event: threading.Event | None = None,
    register_connection: Callable[[HTTPConnection | HTTPSConnection | None], None] | None = None,
    progress_callback: Callable[..., None] | None = None,
) -> tuple[dict[str, object], int]:
    parsed = urlsplit(request.url)
    if parsed.scheme not in {"http", "https"}:
        raise HttpClientError(
            kind="network",
            message=f"unsupported URL scheme: {parsed.scheme}",
        )
    if not parsed.hostname:
        raise HttpClientError(kind="network", message="request URL is missing a hostname")

    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    body_bytes = json.dumps(request.body).encode("utf-8")
    connection = _build_connection(
        parsed.scheme,
        parsed.hostname,
        parsed.port,
        connect_timeout_seconds,
    )
    if register_connection is not None:
        register_connection(connection)
    start = monotonic()

    try:
        _raise_if_cancelled(cancel_event)
        connection.connect()
        _raise_if_cancelled(cancel_event)
        connection.request("POST", path, body=body_bytes, headers=request.headers)
        _raise_if_cancelled(cancel_event)
        response = _await_response_headers(
            connection=connection,
            read_timeout_seconds=read_timeout_seconds,
            start_time=start,
            cancel_event=cancel_event,
        )
        payload_bytes = _read_response_body(
            response=response,
            connection=connection,
            read_timeout_seconds=read_timeout_seconds,
            start_time=start,
            cancel_event=cancel_event,
            progress_callback=progress_callback,
        )
    except _RequestCancelled as exc:
        raise HttpClientError(kind="cancelled", message=str(exc) or "request cancelled") from exc
    except TimeoutError as exc:
        raise HttpClientError(kind="timeout", message=str(exc) or "request timed out") from exc
    except OSError as exc:
        if cancel_event is not None and cancel_event.is_set():
            raise HttpClientError(kind="cancelled", message="request cancelled") from exc
        raise HttpClientError(kind="network", message=str(exc)) from exc
    finally:
        connection.close()
        if register_connection is not None:
            register_connection(None)

    latency_ms = int((monotonic() - start) * 1000)
    text = payload_bytes.decode("utf-8", errors="replace")
    if response.status >= 400:
        message = text.strip() or response.reason or f"HTTP {response.status}"
        raise HttpClientError(
            kind="http_status",
            message=message,
            status_code=response.status,
        )

    payload = _decode_payload(
        request=request,
        response=response,
        text=text,
    )
    return payload, latency_ms


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


def _await_response_headers(
    *,
    connection: HTTPConnection | HTTPSConnection,
    read_timeout_seconds: int,
    start_time: float,
    cancel_event: threading.Event | None = None,
) -> Any:
    while True:
        _raise_if_cancelled(cancel_event)
        remaining = read_timeout_seconds - (monotonic() - start_time)
        if remaining <= 0:
            raise TimeoutError("request timed out")
        sock = connection.sock
        if sock is not None:
            try:
                readable, _, _ = select.select([sock], [], [], min(remaining, 1.0))
            except OSError as exc:
                if cancel_event is not None and cancel_event.is_set():
                    raise _RequestCancelled("request cancelled") from exc
                raise
            if not readable:
                continue
            sock.settimeout(remaining)
        try:
            return connection.getresponse()
        except TimeoutError:
            if cancel_event is not None and cancel_event.is_set():
                raise _RequestCancelled("request cancelled") from None
            continue
        except OSError as exc:
            if _is_idle_timeout_read_error(exc):
                if cancel_event is not None and cancel_event.is_set():
                    raise _RequestCancelled("request cancelled") from None
                continue
            raise


def _read_response_body(
    *,
    response: Any,
    connection: HTTPConnection | HTTPSConnection,
    read_timeout_seconds: int,
    start_time: float,
    cancel_event: threading.Event | None = None,
    progress_callback: Callable[..., None] | None = None,
) -> bytes:
    chunks: list[bytes] = []
    reader = getattr(response, "read1", None)
    uses_buffered_reader = callable(reader)
    while True:
        _raise_if_cancelled(cancel_event)
        elapsed = monotonic() - start_time
        remaining = read_timeout_seconds - elapsed
        if remaining <= 0:
            raise TimeoutError("request timed out")
        sock = connection.sock
        if sock is not None and not uses_buffered_reader:
            try:
                readable, _, _ = select.select([sock], [], [], min(remaining, 1.0))
            except OSError as exc:
                if cancel_event is not None and cancel_event.is_set():
                    raise _RequestCancelled("request cancelled") from exc
                raise
            if not readable:
                continue
        if sock is not None:
            sock.settimeout(remaining)
        try:
            chunk = reader(65536) if uses_buffered_reader else response.read(65536)
        except TimeoutError:
            if cancel_event is not None and cancel_event.is_set():
                raise _RequestCancelled("request cancelled") from None
            continue
        except OSError as exc:
            if _is_idle_timeout_read_error(exc):
                if cancel_event is not None and cancel_event.is_set():
                    raise _RequestCancelled("request cancelled") from None
                continue
            raise
        if not chunk:
            break
        chunks.append(chunk)
        if progress_callback is not None:
            progress_callback(
                len(chunk),
                elapsed_ms=int((monotonic() - start_time) * 1000),
            )
    return b"".join(chunks)


def _should_decode_sse(*, request: HttpRequestSpec, response: Any) -> bool:
    accept = str(request.headers.get("Accept", "")).lower()
    if "text/event-stream" in accept:
        return True
    if request.body.get("stream") is True:
        return True
    content_type = _response_content_type(response).lower()
    return "text/event-stream" in content_type


def _response_content_type(response: Any) -> str:
    getheader = getattr(response, "getheader", None)
    if callable(getheader):
        value = getheader("Content-Type")
        if isinstance(value, str):
            return value
    headers = getattr(response, "headers", None)
    if isinstance(headers, Mapping):
        for key, value in headers.items():
            if str(key).lower() == "content-type" and isinstance(value, str):
                return value
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
        raise _RequestCancelled("request cancelled")


def _is_idle_timeout_read_error(exc: OSError) -> bool:
    message = str(exc).lower()
    return "timed out object" in message or "read operation timed out" in message


def _build_connection(
    scheme: str,
    host: str,
    port: int | None,
    connect_timeout_seconds: int,
) -> HTTPConnection | HTTPSConnection:
    if scheme == "https":
        return HTTPSConnection(
            host=host,
            port=port,
            timeout=connect_timeout_seconds,
            context=ssl.create_default_context(),
        )
    return HTTPConnection(host=host, port=port, timeout=connect_timeout_seconds)
