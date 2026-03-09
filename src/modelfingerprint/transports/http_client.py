from __future__ import annotations

import json
import ssl
from collections.abc import Mapping
from dataclasses import dataclass
from http.client import HTTPConnection, HTTPSConnection
from time import monotonic
from typing import Protocol
from urllib.parse import urlsplit

from modelfingerprint.dialects.base import HttpRequestSpec


@dataclass(eq=False)
class HttpClientError(Exception):
    kind: str
    message: str
    status_code: int | None = None

    def __post_init__(self) -> None:
        super().__init__(self.message)


class HttpClient(Protocol):
    def send(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> tuple[dict[str, object], int]: ...


class StandardHttpClient:
    def send(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
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
        start = monotonic()

        try:
            connection.connect()
            if connection.sock is not None:
                connection.sock.settimeout(read_timeout_seconds)
            connection.request("POST", path, body=body_bytes, headers=request.headers)
            response = connection.getresponse()
            payload_bytes = response.read()
        except TimeoutError as exc:
            raise HttpClientError(kind="timeout", message=str(exc) or "request timed out") from exc
        except OSError as exc:
            raise HttpClientError(kind="network", message=str(exc)) from exc
        finally:
            connection.close()

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
