from __future__ import annotations

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.extractors._v2_helpers import (
    evidence_slot_count,
    object_mapping,
    prompt_reference,
    ratio,
    require_payload,
    string_list,
)
from modelfingerprint.extractors.base import FeatureMap


def extract_evidence_grounding(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="evidence_grounding_v1")
    task_result = object_mapping(payload.get("task_result", {}), field_name="task_result")
    evidence = object_mapping(payload.get("evidence", {}), field_name="evidence")
    unknown_fields = string_list(payload.get("unknown_fields", []), field_name="unknown_fields")
    violations = string_list(payload.get("violations", []), field_name="violations")
    filled_field_count = sum(value is not None for value in task_result.values())

    return {
        "filled_field_count": filled_field_count,
        "unknown_field_count": len(unknown_fields),
        "evidence_field_count": evidence_slot_count(evidence),
        "violation_count": len(violations),
    }


def score_evidence_grounding(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("evidence_grounding_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="evidence_grounding_score_v1")
    task_result = object_mapping(payload.get("task_result", {}), field_name="task_result")
    evidence = object_mapping(payload.get("evidence", {}), field_name="evidence")
    unknown_fields = set(
        string_list(payload.get("unknown_fields", []), field_name="unknown_fields")
    )
    violations = string_list(payload.get("violations", []), field_name="violations")
    expected = object_mapping(
        prompt_reference(prompt, key="expected_task_result"),
        field_name="expected_task_result",
    )

    total_fields = len(expected)
    value_matches = sum(task_result.get(name) == value for name, value in expected.items())
    nullable_fields = [name for name, value in expected.items() if value is None]
    abstention_hits = sum(
        task_result.get(name) is None or name in unknown_fields for name in nullable_fields
    )
    required_fields = [name for name, value in expected.items() if value is not None]
    evidence_hits = sum(
        evidence_slot_count({name: evidence.get(name)}) > 0
        for name in required_fields
        if task_result.get(name) == expected[name]
    )

    return {
        "value_accuracy": ratio(value_matches, total_fields),
        "abstention_compliance": ratio(abstention_hits, len(nullable_fields)),
        "evidence_alignment": ratio(evidence_hits, len(required_fields)),
        "violation_free": len(violations) == 0,
    }
