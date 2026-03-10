from __future__ import annotations

import json
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
        handle = self.start(
            request,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
        )
        terminal = handle.wait_until_terminal(
            timeout_seconds=float(connect_timeout_seconds + read_timeout_seconds + 5),
        )
        if terminal is None:
            handle.cancel()
            raise HttpClientError(kind="timeout", message="request timed out")
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
        if connection.sock is not None:
            connection.sock.settimeout(min(read_timeout_seconds, 1.0))
        connection.request("POST", path, body=body_bytes, headers=request.headers)
        _raise_if_cancelled(cancel_event)
        response = connection.getresponse()
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

    try:
        payload = json.loads(text)
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

    return dict(payload), latency_ms


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
    while True:
        _raise_if_cancelled(cancel_event)
        elapsed = monotonic() - start_time
        remaining = read_timeout_seconds - elapsed
        if remaining <= 0:
            raise TimeoutError("request timed out")
        if connection.sock is not None:
            connection.sock.settimeout(min(remaining, 1.0))
        try:
            chunk = reader(65536) if callable(reader) else response.read(65536)
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


def _raise_if_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise _RequestCancelled("request cancelled")


def _is_idle_timeout_read_error(exc: OSError) -> bool:
    return "timed out object" in str(exc).lower()


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
