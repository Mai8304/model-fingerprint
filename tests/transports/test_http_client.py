from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass

import httpx
import pytest

from modelfingerprint.dialects.base import HttpRequestSpec
from modelfingerprint.transports.http_client import HttpClientError, StandardHttpClient


@dataclass(frozen=True)
class ChunkEvent:
    delay_seconds: float
    data: bytes | None = None
    error: Exception | None = None


class FakeAsyncResponse:
    def __init__(
        self,
        events: list[ChunkEvent],
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        reason_phrase: str = "OK",
    ) -> None:
        self.status_code = status_code
        self.reason_phrase = reason_phrase
        self.headers = headers or {"Content-Type": "application/json"}
        self._events = list(events)
        self.closed = False

    async def aiter_bytes(self):
        for event in self._events:
            await asyncio.sleep(event.delay_seconds)
            if event.error is not None:
                raise event.error
            if event.data is not None:
                yield event.data

    async def aclose(self) -> None:
        self.closed = True


class FakeStreamContext:
    def __init__(
        self,
        response: FakeAsyncResponse | None,
        *,
        enter_delay_seconds: float = 0.0,
        enter_error: Exception | None = None,
    ) -> None:
        self._response = response
        self._enter_delay_seconds = enter_delay_seconds
        self._enter_error = enter_error

    async def __aenter__(self) -> FakeAsyncResponse:
        await asyncio.sleep(self._enter_delay_seconds)
        if self._enter_error is not None:
            raise self._enter_error
        assert self._response is not None
        return self._response

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        if self._response is not None:
            await self._response.aclose()
        return False


class FakeAsyncClient:
    def __init__(self, stream_context: FakeStreamContext, **kwargs) -> None:
        self.stream_context = stream_context
        self.kwargs = kwargs
        self.stream_calls: list[dict[str, object]] = []
        self.closed = False

    def stream(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, object],
    ) -> FakeStreamContext:
        self.stream_calls.append(
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "json": dict(json),
            }
        )
        return self.stream_context

    async def aclose(self) -> None:
        self.closed = True


def build_request() -> HttpRequestSpec:
    return HttpRequestSpec(
        url="https://example.test/v1/chat/completions",
        headers={"Content-Type": "application/json"},
        body={"model": "opaque", "messages": [{"role": "user", "content": "ok"}]},
    )


def build_stream_request() -> HttpRequestSpec:
    return HttpRequestSpec(
        url="https://example.test/v1/chat/completions",
        headers={
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
        body={
            "model": "opaque",
            "messages": [{"role": "user", "content": "ok"}],
            "stream": True,
        },
    )


def wait_until(predicate, *, timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("timed out waiting for condition")


def patch_async_client(
    monkeypatch: pytest.MonkeyPatch,
    stream_context: FakeStreamContext,
) -> list[FakeAsyncClient]:
    created: list[FakeAsyncClient] = []

    def fake_async_client(**kwargs) -> FakeAsyncClient:
        instance = FakeAsyncClient(stream_context, **kwargs)
        created.append(instance)
        return instance

    monkeypatch.setattr(
        "modelfingerprint.transports.http_client.httpx.AsyncClient",
        fake_async_client,
    )
    return created


def test_standard_http_client_send_posts_json_through_httpx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = patch_async_client(
        monkeypatch,
        FakeStreamContext(
            FakeAsyncResponse([ChunkEvent(delay_seconds=0.0, data=b'{"ok":true}')]),
        ),
    )

    payload, latency_ms = StandardHttpClient().send(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=30,
    )

    assert payload == {"ok": True}
    assert latency_ms >= 0
    assert len(created) == 1
    assert created[0].stream_calls == [
        {
            "method": "POST",
            "url": "https://example.test/v1/chat/completions",
            "headers": {"Content-Type": "application/json"},
            "json": {"model": "opaque", "messages": [{"role": "user", "content": "ok"}]},
        }
    ]
    timeout = created[0].kwargs["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 5
    assert timeout.read is None


def test_standard_http_client_send_classifies_connect_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_async_client(
        monkeypatch,
        FakeStreamContext(
            None,
            enter_error=httpx.ConnectTimeout("connect timed out"),
        ),
    )

    with pytest.raises(HttpClientError) as exc_info:
        StandardHttpClient().send(
            build_request(),
            connect_timeout_seconds=5,
            read_timeout_seconds=30,
        )

    assert exc_info.value.kind == "connect_timeout"


def test_standard_http_client_send_classifies_first_byte_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_async_client(
        monkeypatch,
        FakeStreamContext(
            FakeAsyncResponse([ChunkEvent(delay_seconds=0.1, data=b'{"ok":true}')]),
        ),
    )

    with pytest.raises(HttpClientError) as exc_info:
        StandardHttpClient(
            first_byte_timeout_seconds=0.01,
            idle_timeout_seconds=0.5,
        ).send(
            build_request(),
            connect_timeout_seconds=5,
            read_timeout_seconds=1,
        )

    assert exc_info.value.kind == "first_byte_timeout"


def test_standard_http_client_send_classifies_idle_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_async_client(
        monkeypatch,
        FakeStreamContext(
            FakeAsyncResponse(
                [
                    ChunkEvent(delay_seconds=0.0, data=b'{"ok":'),
                    ChunkEvent(delay_seconds=0.1, data=b"true}"),
                ]
            ),
        ),
    )

    with pytest.raises(HttpClientError) as exc_info:
        StandardHttpClient(
            first_byte_timeout_seconds=0.5,
            idle_timeout_seconds=0.01,
        ).send(
            build_request(),
            connect_timeout_seconds=5,
            read_timeout_seconds=1,
        )

    assert exc_info.value.kind == "idle_timeout"


def test_standard_http_client_send_classifies_total_deadline_exceeded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_async_client(
        monkeypatch,
        FakeStreamContext(
            FakeAsyncResponse(
                [
                    ChunkEvent(delay_seconds=0.0, data=b'{"ok":'),
                    ChunkEvent(delay_seconds=0.1, data=b"true}"),
                ]
            ),
        ),
    )

    with pytest.raises(HttpClientError) as exc_info:
        StandardHttpClient(
            first_byte_timeout_seconds=0.5,
            idle_timeout_seconds=0.5,
        ).send(
            build_request(),
            connect_timeout_seconds=5,
            read_timeout_seconds=0.05,
        )

    assert exc_info.value.kind == "total_deadline_exceeded"


def test_start_exposes_progress_before_terminal_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_async_client(
        monkeypatch,
        FakeStreamContext(
            FakeAsyncResponse(
                [
                    ChunkEvent(delay_seconds=0.01, data=b'{"ok":'),
                    ChunkEvent(delay_seconds=0.2, data=b"true}"),
                ]
            ),
        ),
    )

    handle = StandardHttpClient().start(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=1,
    )

    initial = handle.snapshot()
    assert initial.bytes_received == 0
    assert initial.has_any_data is False
    assert initial.completed is False

    wait_until(lambda: handle.snapshot().bytes_received > 0)
    partial = handle.snapshot()
    assert partial.has_any_data is True
    assert partial.first_byte_latency_ms is not None
    assert partial.completed is False

    terminal = handle.wait_until_terminal(timeout_seconds=1.0)
    assert terminal is not None
    assert terminal.error is None
    assert terminal.payload == {"ok": True}


def test_start_parses_sse_stream_into_terminal_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_async_client(
        monkeypatch,
        FakeStreamContext(
            FakeAsyncResponse(
                [
                    ChunkEvent(
                        delay_seconds=0.0,
                        data=(
                            b'data: {"choices":[{"index":0,"delta":{"content":"ok "}}]}\n\n'
                            b'data: {"choices":[{"index":0,"delta":{"content":"done"},"finish_reason":"stop"}],'
                            b'"usage":{"prompt_tokens":1,"completion_tokens":2,"total_tokens":3}}\n\n'
                            b"data: [DONE]\n\n"
                        ),
                    ),
                ],
                headers={"Content-Type": "text/event-stream"},
            ),
        ),
    )

    handle = StandardHttpClient().start(
        build_stream_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=1,
    )
    terminal = handle.wait_until_terminal(timeout_seconds=1.0)

    assert terminal is not None
    assert terminal.error is None
    assert terminal.payload == {
        "choices": [
            {
                "finish_reason": "stop",
                "index": 0,
                "message": {"content": "ok done"},
            }
        ],
        "usage": {
            "completion_tokens": 2,
            "prompt_tokens": 1,
            "total_tokens": 3,
        },
    }


def test_start_cancellation_settles_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_async_client(
        monkeypatch,
        FakeStreamContext(
            FakeAsyncResponse([ChunkEvent(delay_seconds=0.2, data=b'{"ok":true}')]),
        ),
    )

    handle = StandardHttpClient().start(
        build_request(),
        connect_timeout_seconds=5,
        read_timeout_seconds=1,
    )

    wait_until(lambda: handle.snapshot().elapsed_ms > 0)
    handle.cancel()
    terminal = handle.wait_until_terminal(timeout_seconds=1.0)

    assert terminal is not None
    assert terminal.payload is None
    assert terminal.error is not None
    assert terminal.error.kind == "cancelled"
