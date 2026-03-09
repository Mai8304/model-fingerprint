from __future__ import annotations

import json
import re
from collections.abc import Mapping

from modelfingerprint.canonicalizers.base import CanonicalizationError, CanonicalizerResult
from modelfingerprint.contracts.run import CanonicalizationEvent, CanonicalizedOutput

FENCE_BLOCK_PATTERN = re.compile(r"```[a-zA-Z0-9_-]*\n?(.*?)```", re.DOTALL)
TOP_LEVEL_KEY_ALIASES = {
    "result": "task_result",
    "evidence_map": "evidence",
    "unknown_fields": "unknowns",
}


def canonicalize_tolerant_json(raw_output: str) -> CanonicalizerResult:
    text = raw_output.strip()
    events: list[CanonicalizationEvent] = []

    candidate, prefix_text, suffix_text = _strip_embedded_fence(text)
    if candidate != text:
        events.append(
            CanonicalizationEvent(code="removed_fence", message="removed markdown fence")
        )
    payload, object_prefix, object_suffix = _extract_first_json_object(candidate)
    if prefix_text.strip() or object_prefix.strip():
        events.append(
            CanonicalizationEvent(
                code="stripped_prefix_text",
                message="removed explanatory text before JSON object",
            )
        )
    if suffix_text.strip() or object_suffix.strip():
        events.append(
            CanonicalizationEvent(
                code="stripped_suffix_text",
                message="removed explanatory text after JSON object",
            )
        )

    normalized_payload = _normalize_top_level_aliases(payload)
    if normalized_payload != payload:
        events.append(
            CanonicalizationEvent(
                code="normalized_key_alias",
                message="normalized top-level key aliases to canonical names",
            )
        )

    return CanonicalizedOutput(format_id="tolerant_json_v3", payload=normalized_payload), events


def _strip_embedded_fence(text: str) -> tuple[str, str, str]:
    match = FENCE_BLOCK_PATTERN.search(text)
    if match is None:
        return text, "", ""
    prefix = text[: match.start()]
    suffix = text[match.end() :]
    return match.group(1).strip(), prefix, suffix


def _extract_first_json_object(text: str) -> tuple[dict[str, object], str, str]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            payload, end_index = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            raise CanonicalizationError(
                code="invalid_json_shape",
                message="response body must be a JSON object",
            )
        return dict(payload), text[:index], text[index + end_index :]
    raise CanonicalizationError(
        code="invalid_json",
        message="response body must contain a JSON object",
    )


def _normalize_top_level_aliases(payload: dict[str, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, value in payload.items():
        normalized[TOP_LEVEL_KEY_ALIASES.get(key, key)] = value
    return normalized
