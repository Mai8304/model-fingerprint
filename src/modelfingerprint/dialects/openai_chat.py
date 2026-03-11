from __future__ import annotations

import json
import re
from collections.abc import Mapping

from modelfingerprint.canonicalizers._common import strip_markdown_fence
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import NormalizedCompletion, UsageMetadata
from modelfingerprint.dialects.base import HttpRequestSpec, resolve_path
from modelfingerprint.http_defaults import DEFAULT_BROWSER_USER_AGENT

FENCE_BLOCK_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n?(.*?)```", re.DOTALL)
COMMON_REASONING_FIELDS = ("reasoning_content", "reasoning", "thinking")


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
                "User-Agent": DEFAULT_BROWSER_USER_AGENT,
                **_openrouter_headers(str(endpoint.base_url)),
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
        answer = resolve_path(payload, endpoint.response_mapping.answer_text_path)
        answer_text = _coerce_optional_text(answer) or ""

        reasoning = resolve_path(payload, endpoint.response_mapping.reasoning_text_path)
        reasoning_text = _coerce_optional_text(reasoning) or _infer_reasoning_text(payload)
        if answer_text == "" and reasoning_text is not None:
            recovered_answer = _recover_answer_from_reasoning(reasoning_text)
            if recovered_answer is not None:
                answer_text = recovered_answer
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


def _coerce_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, Mapping):
        text_value = value.get("text")
        if isinstance(text_value, str):
            text = text_value.strip()
            return text or None
        return None
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            text = _coerce_optional_text(item)
            if text is not None:
                parts.append(text)
        if parts:
            return "\n".join(parts)
        return None
    return str(value)


def _infer_reasoning_text(payload: Mapping[str, object]) -> str | None:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
        return None
    message = choices[0].get("message")
    if not isinstance(message, Mapping):
        return None

    for field in COMMON_REASONING_FIELDS:
        reasoning_text = _coerce_optional_text(message.get(field))
        if reasoning_text is not None:
            return reasoning_text

    details = message.get("reasoning_details")
    if not isinstance(details, list):
        return None
    parts: list[str] = []
    for item in details:
        if not isinstance(item, Mapping):
            continue
        text = _coerce_optional_text(item.get("text"))
        if text is not None:
            parts.append(text)
    if parts:
        return "\n\n".join(parts)
    return None


def _recover_answer_from_reasoning(reasoning_text: str) -> str | None:
    fenced_candidates = [
        match.group(1).strip() for match in FENCE_BLOCK_PATTERN.finditer(reasoning_text)
    ]
    for candidate in reversed(fenced_candidates):
        recovered = _validated_json_object(candidate)
        if recovered is not None:
            return recovered

    unfenced_reasoning, _ = strip_markdown_fence(reasoning_text)
    return _extract_last_json_object(unfenced_reasoning)


def _extract_last_json_object(text: str) -> str | None:
    decoder = json.JSONDecoder()
    last_object: str | None = None
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, end_index = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            last_object = text[index : index + end_index].strip()
    return last_object


def _validated_json_object(candidate: str) -> str | None:
    stripped = candidate.strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, Mapping):
        return None
    return stripped


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


def _openrouter_headers(base_url: str) -> dict[str, str]:
    if "openrouter.ai" not in base_url:
        return {}
    return {
        "HTTP-Referer": "https://codex.local",
        "X-Title": "Codex Model Fingerprint",
    }
