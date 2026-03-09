from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import NormalizedCompletion, UsageMetadata
from modelfingerprint.dialects.base import HttpRequestSpec, resolve_path


class OpenAIChatDialectAdapter:
    def build_request(
        self,
        prompt: PromptDefinition,
        endpoint: EndpointProfile,
        api_key: str,
        *,
        output_token_cap: int | None = None,
        body_overrides: Mapping[str, object] | None = None,
    ) -> HttpRequestSpec:
        body: dict[str, object] = {
            "model": endpoint.model,
            "messages": [message.model_dump(mode="json") for message in prompt.messages],
            "temperature": prompt.generation.temperature,
            "top_p": prompt.generation.top_p,
        }
        if endpoint.request_mapping.static_body:
            _merge_mapping(body, endpoint.request_mapping.static_body)
        body[endpoint.request_mapping.output_token_cap_field] = (
            prompt.generation.max_output_tokens
            if output_token_cap is None
            else output_token_cap
        )
        if prompt.generation.response_format == "json_object":
            body["response_format"] = endpoint.request_mapping.json_response_shape
        if body_overrides:
            _merge_mapping(body, body_overrides)

        return HttpRequestSpec(
            url=f"{str(endpoint.base_url).rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body=body,
        )

    def parse_response(
        self,
        endpoint: EndpointProfile,
        payload: Mapping[str, object],
        *,
        latency_ms: int | None = None,
        raw_response_path: str | None = None,
    ) -> NormalizedCompletion:
        answer_text = str(resolve_path(payload, endpoint.response_mapping.answer_text_path) or "")
        reasoning = resolve_path(payload, endpoint.response_mapping.reasoning_text_path)
        reasoning_text = None if reasoning is None else str(reasoning)
        usage_paths = endpoint.response_mapping.usage_paths

        return NormalizedCompletion(
            answer_text=answer_text,
            reasoning_text=reasoning_text,
            reasoning_visible=reasoning_text is not None and reasoning_text != "",
            finish_reason=_as_optional_str(
                resolve_path(payload, endpoint.response_mapping.finish_reason_path)
            ),
            latency_ms=latency_ms,
            raw_response_path=raw_response_path,
            usage=UsageMetadata(
                input_tokens=_as_int(resolve_path(payload, usage_paths.prompt_tokens)),
                output_tokens=_as_int(resolve_path(payload, usage_paths.output_tokens)),
                reasoning_tokens=_as_int(resolve_path(payload, usage_paths.reasoning_tokens)),
                total_tokens=_as_int(resolve_path(payload, usage_paths.total_tokens)),
            ),
        )


def _as_int(value: object | None) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        raise ValueError("usage fields must not be boolean")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise ValueError(f"expected int-compatible usage value, got {type(value).__name__}")


def _as_optional_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def _merge_mapping(target: dict[str, object], updates: Mapping[str, object]) -> None:
    for key, value in updates.items():
        current = target.get(key)
        if isinstance(current, Mapping) and isinstance(value, Mapping):
            merged = dict(current)
            _merge_mapping(merged, value)
            target[key] = merged
            continue
        if isinstance(value, Mapping):
            nested: dict[str, object] = {}
            _merge_mapping(nested, value)
            target[key] = nested
            continue
        target[key] = value
