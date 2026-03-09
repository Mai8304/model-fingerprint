from __future__ import annotations

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.extractors._v2_helpers import (
    object_mapping,
    prompt_reference,
    ratio,
    require_payload,
    string_list,
)
from modelfingerprint.extractors.base import FeatureMap


def extract_state_tracking(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="state_tracking_v1")
    task_result = object_mapping(payload.get("task_result", {}), field_name="task_result")
    derivation_codes = _mapping_or_empty(payload.get("derivation_codes"))
    defaults_used = _defaults_used(payload.get("defaults_used", []))
    violations = string_list(payload.get("violations", []), field_name="violations")

    return {
        "resolved_object_count": len(task_result),
        "derivation_count": len(derivation_codes),
        "default_count": len(defaults_used),
        "violation_count": len(violations),
    }


def score_state_tracking(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("state_tracking_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="state_tracking_score_v1")
    task_result = object_mapping(payload.get("task_result", {}), field_name="task_result")
    derivation_codes = _mapping_or_empty(payload.get("derivation_codes"))
    defaults_used = set(_defaults_used(payload.get("defaults_used", [])))
    violations = string_list(payload.get("violations", []), field_name="violations")

    expected_task_result = object_mapping(
        prompt_reference(prompt, key="expected_task_result"),
        field_name="expected_task_result",
    )
    expected_derivations = object_mapping(
        prompt_reference(prompt, key="expected_derivation_codes"),
        field_name="expected_derivation_codes",
    )
    expected_defaults = set(
        string_list(
            prompt_reference(prompt, key="expected_defaults_used"),
            field_name="expected_defaults_used",
        )
    )

    leaf_matches = 0
    leaf_total = 0
    for object_id, expected_snapshot in expected_task_result.items():
        observed_snapshot = object_mapping(
            expected_snapshot,
            field_name=f"expected_task_result.{object_id}",
        )
        actual_snapshot = object_mapping(
            task_result.get(object_id, {}),
            field_name=f"task_result.{object_id}",
        )
        for field_name, expected_value in observed_snapshot.items():
            leaf_total += 1
            if actual_snapshot.get(field_name) == expected_value:
                leaf_matches += 1

    derivation_hits = sum(
        derivation_codes.get(object_id) == expected_value
        for object_id, expected_value in expected_derivations.items()
    )
    default_hits = len(defaults_used & expected_defaults)

    return {
        "snapshot_accuracy": ratio(leaf_matches, leaf_total),
        "derivation_accuracy": ratio(derivation_hits, len(expected_derivations)),
        "default_usage_accuracy": ratio(default_hits, len(expected_defaults)),
        "violation_free": len(violations) == 0,
    }


def _mapping_or_empty(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    return {}


def _defaults_used(value: object) -> list[str]:
    if isinstance(value, dict):
        return _flatten_paths(value)
    return string_list(value, field_name="defaults_used")


def _flatten_paths(value: dict[str, object], prefix: str = "") -> list[str]:
    flattened: list[str] = []
    for key, item in value.items():
        path = key if prefix == "" else f"{prefix}.{key}"
        if isinstance(item, dict):
            nested = _flatten_paths(
                {str(child_key): child for child_key, child in item.items()},
                path,
            )
            if nested:
                flattened.extend(nested)
                continue
        flattened.append(path)
    return flattened
