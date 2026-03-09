from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import NormalizedCompletion


class HttpRequestSpec:
    def __init__(self, url: str, headers: dict[str, str], body: dict[str, object]) -> None:
        self.url = url
        self.headers = headers
        self.body = body


class DialectAdapter(Protocol):
    def build_request(
        self,
        prompt: PromptDefinition,
        endpoint: EndpointProfile,
        api_key: str,
    ) -> HttpRequestSpec: ...

    def parse_response(
        self,
        endpoint: EndpointProfile,
        payload: Mapping[str, object],
        *,
        latency_ms: int | None = None,
        raw_response_path: str | None = None,
    ) -> NormalizedCompletion: ...


def resolve_path(payload: Mapping[str, object], dotted_path: str | None) -> object | None:
    if not dotted_path:
        return None

    current: object = payload
    for part in dotted_path.split("."):
        if isinstance(current, Mapping):
            current = current.get(part)
            continue
        if isinstance(current, list):
            current = current[int(part)]
            continue
        return None
    return current
