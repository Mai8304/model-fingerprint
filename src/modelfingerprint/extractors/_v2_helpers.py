from __future__ import annotations

from collections.abc import Mapping, Sequence

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput


def require_payload(canonical_output: object, *, extractor_name: str) -> Mapping[str, object]:
    if not isinstance(canonical_output, CanonicalizedOutput):
        raise TypeError(f"{extractor_name} expects CanonicalizedOutput input")
    payload = canonical_output.payload
    if not isinstance(payload, Mapping):
        raise TypeError(f"{extractor_name} canonical payload must be a mapping")
    return payload


def object_mapping(value: object, *, field_name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def string_mapping(value: object, *, field_name: str) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return {str(key): str(item) for key, item in value.items()}


def string_list(value: object, *, field_name: str) -> list[str]:
    if value is None or value is False:
        return []
    if isinstance(value, str):
        return [value]
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{field_name} must be a list of strings")
    result: list[str] = []
    for item in value:
        result.append(str(item))
    return result


def prompt_reference(prompt: PromptDefinition, *, key: str) -> object:
    if prompt.evaluation is None:
        raise TypeError("prompt evaluation reference is required for score extractors")
    if key not in prompt.evaluation.reference:
        raise TypeError(f"prompt evaluation reference is missing {key}")
    return prompt.evaluation.reference[key]


def evidence_slot_count(mapping: Mapping[str, object]) -> int:
    count = 0
    for value in mapping.values():
        if value is None or value is False:
            continue
        if isinstance(value, str):
            if value.strip():
                count += 1
            continue
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            if len(value) > 0:
                count += 1
            continue
        count += 1
    return count


def ratio(matches: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return matches / total
