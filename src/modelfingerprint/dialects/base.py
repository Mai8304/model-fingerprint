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
        *,
        output_token_cap: int | None = None,
        body_overrides: Mapping[str, object] | None = None,
    ) -> HttpRequestSpec: ...

    def parse_response(
        self,
        endpoint: EndpointProfile,
        payload: Mapping[str, object],
        *,
        latency_ms: int | None = None,
        raw_response_path: str | None = None,
    ) -> NormalizedCompletion: ...


def build_protocol_family_adapter(endpoint: EndpointProfile) -> DialectAdapter:
    if endpoint.protocol_family == "openai_compatible":
        from modelfingerprint.dialects.openai_chat import OpenAICompatibleAdapter

        return OpenAICompatibleAdapter()
    raise ValueError(f"unsupported protocol family: {endpoint.protocol_family}")


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
