from __future__ import annotations

import threading
import time

import pytest

from modelfingerprint.dialects.base import HttpRequestSpec
from modelfingerprint.transports.http_client import HttpClientError, StandardHttpClient


class FakeSocket:
    def __init__(self) -> None:
        self.timeouts: list[float] = []

    def settimeout(self, value: float) -> None:
        self.timeouts.append(value)


class FakeResponse:
    def __init__(self, chunks: list[bytes], clock: dict[str, float]) -> None:
        self.status = 200
        self.reason = "OK"
        self._chunks = list(chunks)
        self._clock = clock

    def read(self, amt: int | None = None) -> bytes:
        if not self._chunks:
            return b""
        self._clock["now"] += 11.0
        return self._chunks.pop(0)


class FakeStreamingResponse(FakeResponse):
    def read(self, amt: int | None = None) -> bytes:
        raise AssertionError("read() should not be used when read1() is available")

    def read1(self, amt: int | None = None) -> bytes:
        if not self._chunks:
            return b""
        self._clock["now"] += 11.0
        return self._chunks.pop(0)


class ControlledStreamingResponse:
    def __init__(
        self,
        chunks: list[bytes],
        release_events: list[threading.Event],
        *,
        closed_event: threading.Event,
    ) -> None:
        self.status = 200
        self.reason = "OK"
        self._chunks = list(chunks)
        self._release_events = list(release_events)
        self._closed_event = closed_event

    def read1(self, amt: int | None = None) -> bytes:
        if self._closed_event.is_set():
            raise OSError("connection closed")
        if not self._chunks:
            return b""
        event = self._release_events[0]
        if not event.wait(0.01):
            raise TimeoutError("waiting for response bytes")
        self._release_events.pop(0)
        return self._chunks.pop(0)


class TimedOutObjectResponse(ControlledStreamingResponse):
    def read1(self, amt: int | None = None) -> bytes:
        if self._closed_event.is_set():
            raise OSError("connection closed")
        if not self._chunks:
            return b""
        event = self._release_events[0]
        if not event.wait(0.01):
            raise OSError("cannot read from timed out object")
        self._release_events.pop(0)
        return self._chunks.pop(0)


class FakeConnection:
    def __init__(self, response: object) -> None:
        self.sock = FakeSocket()
        self._response = response

    def connect(self) -> None:
        return None

    def request(self, method: str, path: str, body: bytes, headers: dict[str, str]) -> None:
        return None

    def getresponse(self) -> object:
        return self._response

    def close(self) -> None:
        return None


class ClosableFakeConnection(FakeConnection):
    def __init__(self, response: object, closed_event: threading.Event) -> None:
        super().__init__(response)
        self._closed_event = closed_event

    def close(self) -> None:
        self._closed_event.set()


def build_request() -> HttpRequestSpec:
    return HttpRequestSpec(
        url="https://example.test/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        body={"model": "opaque", "messages": [{"role": "user", "content": "ok"}]},
    )


def wait_until(predicate, *, timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("timed out waiting for condition")


def test_standard_http_client_enforces_total_read_window(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 0.0}
    response = FakeResponse(
        chunks=[b"{", b'"ok":', b"true}"],
        clock=clock,
    )
    connection = FakeConnection(response)
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client._build_connection",
        lambda scheme, host, port, connect_timeout_seconds: connection,
    )
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client.monotonic",
        lambda: clock["now"],
    )

    client = StandardHttpClient()

    with pytest.raises(HttpClientError) as exc_info:
        client.send(
            build_request(),
            connect_timeout_seconds=5,
            read_timeout_seconds=30,
        )

    assert exc_info.value.kind == "timeout"


def test_standard_http_client_reads_json_within_total_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"now": 0.0}
    response = FakeResponse(
        chunks=[b'{"ok":', b"true}"],
        clock=clock,
    )
    connection = FakeConnection(response)
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client._build_connection",
        lambda scheme, host, port, connect_timeout_seconds: connection,
    )
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client.monotonic",
        lambda: clock["now"],
    )

    payload, latency_ms = StandardHttpClient().send(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=30,
    )

    assert payload == {"ok": True}
    assert latency_ms == 22000
    assert connection.sock.timeouts


def test_standard_http_client_prefers_read1_when_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = {"now": 0.0}
    response = FakeStreamingResponse(
        chunks=[b'{"ok":', b"true}"],
        clock=clock,
    )
    connection = FakeConnection(response)
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client._build_connection",
        lambda scheme, host, port, connect_timeout_seconds: connection,
    )
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client.monotonic",
        lambda: clock["now"],
    )

    payload, latency_ms = StandardHttpClient().send(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=30,
    )

    assert payload == {"ok": True}
    assert latency_ms == 22000


def test_start_exposes_progress_before_terminal_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_event = threading.Event()
    release_one = threading.Event()
    release_two = threading.Event()
    response = ControlledStreamingResponse(
        chunks=[b'{"ok":', b"true}"],
        release_events=[release_one, release_two],
        closed_event=closed_event,
    )
    connection = ClosableFakeConnection(response, closed_event)
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client._build_connection",
        lambda scheme, host, port, connect_timeout_seconds: connection,
    )

    handle = StandardHttpClient().start(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=30,
    )

    initial = handle.snapshot()
    assert initial.bytes_received == 0
    assert initial.has_any_data is False
    assert initial.completed is False

    release_one.set()
    wait_until(lambda: handle.snapshot().bytes_received > 0)

    partial = handle.snapshot()
    assert partial.has_any_data is True
    assert partial.first_byte_latency_ms is not None
    assert partial.completed is False

    release_two.set()
    terminal = handle.wait_until_terminal(timeout_seconds=1.0)

    assert terminal is not None
    assert terminal.error is None
    assert terminal.payload == {"ok": True}
    assert terminal.latency_ms is not None

    final = handle.snapshot()
    assert final.completed is True
    assert final.bytes_received >= len(b'{"ok":true}')


def test_start_cancellation_settles_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_event = threading.Event()
    release_one = threading.Event()
    response = ControlledStreamingResponse(
        chunks=[b'{"ok":'],
        release_events=[release_one],
        closed_event=closed_event,
    )
    connection = ClosableFakeConnection(response, closed_event)
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client._build_connection",
        lambda scheme, host, port, connect_timeout_seconds: connection,
    )

    handle = StandardHttpClient().start(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=30,
    )

    wait_until(lambda: handle.snapshot().elapsed_ms > 0)
    handle.cancel()
    terminal = handle.wait_until_terminal(timeout_seconds=1.0)

    assert terminal is not None
    assert terminal.payload is None
    assert terminal.error is not None
    assert terminal.error.kind == "cancelled"


def test_standard_http_client_treats_timed_out_object_reads_as_idle_waits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    closed_event = threading.Event()
    release_one = threading.Event()
    release_two = threading.Event()
    response = TimedOutObjectResponse(
        chunks=[b'{"ok":', b"true}"],
        release_events=[release_one, release_two],
        closed_event=closed_event,
    )
    connection = ClosableFakeConnection(response, closed_event)
    monkeypatch.setattr(
        "modelfingerprint.transports.http_client._build_connection",
        lambda scheme, host, port, connect_timeout_seconds: connection,
    )

    handle = StandardHttpClient().start(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=30,
    )

    release_one.set()
    wait_until(lambda: handle.snapshot().bytes_received > 0)
    release_two.set()
    terminal = handle.wait_until_terminal(timeout_seconds=1.0)

    assert terminal is not None
    assert terminal.error is None
    assert terminal.payload == {"ok": True}
