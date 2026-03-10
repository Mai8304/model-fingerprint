from __future__ import annotations

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


class FakeConnection:
    def __init__(self, response: FakeResponse) -> None:
        self.sock = FakeSocket()
        self._response = response

    def connect(self) -> None:
        return None

    def request(self, method: str, path: str, body: bytes, headers: dict[str, str]) -> None:
        return None

    def getresponse(self) -> FakeResponse:
        return self._response

    def close(self) -> None:
        return None


def build_request() -> HttpRequestSpec:
    return HttpRequestSpec(
        url="https://example.test/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        body={"model": "opaque", "messages": [{"role": "user", "content": "ok"}]},
    )


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
