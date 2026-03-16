from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.extractors._shared_helpers import (
    evidence_slot_count,
    object_mapping,
    prompt_reference,
    ratio,
    require_payload,
)
from modelfingerprint.extractors._v3_helpers import (
    shared_evidence,
    shared_task_result,
    shared_violations,
)
from modelfingerprint.extractors.base import FeatureMap


def extract_boundary_decision_v1(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="boundary_decision_v1")
    task_result = shared_task_result(payload)
    evidence = shared_evidence(payload)
    violations = shared_violations(payload)

    answered = 0
    unknown = 0
    conflict = 0
    feature_map: FeatureMap = {}
    for question_id, value in task_result.items():
        slot = _decision_slot(value, field_name="task_result", strict=False)
        status = slot.get("s")
        if status == "a":
            answered += 1
        elif status == "u":
            unknown += 1
        elif status == "c":
            conflict += 1
        feature_map[f"status_{question_id}"] = status
        if slot.get("v") is not None:
            feature_map[f"value_{question_id}"] = slot.get("v")

    return {
        "answered_count": answered,
        "unknown_count": unknown,
        "conflict_count": conflict,
        "evidence_field_count": evidence_slot_count(evidence),
        "violation_count": len(violations),
        **feature_map,
    }


def score_boundary_decision_v1(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("boundary_decision_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="boundary_decision_score_v1")
    task_result = shared_task_result(payload)
    evidence = shared_evidence(payload)
    violations = shared_violations(payload)
    expected_task_result = object_mapping(
        prompt_reference(prompt, key="expected_task_result"),
        field_name="expected_task_result",
    )

    exact_matches = 0
    status_matches = 0
    total = 0
    feature_map: FeatureMap = {}
    for question_id, expected_value in expected_task_result.items():
        total += 1
        expected_slot = _decision_slot(
            expected_value,
            field_name=f"expected_task_result.{question_id}",
            strict=True,
        )
        actual_slot = _decision_slot(
            task_result.get(question_id, {}),
            field_name=f"task_result.{question_id}",
            strict=False,
        )
        feature_map[f"match_{question_id}"] = actual_slot == expected_slot
        if actual_slot == expected_slot:
            exact_matches += 1
        if actual_slot.get("s") == expected_slot.get("s"):
            status_matches += 1
    evidence_hits = sum(_has_evidence(value) for value in evidence.values())
    evidence_total = len(evidence)

    return {
        "decision_accuracy": ratio(exact_matches, total),
        "boundary_accuracy": ratio(status_matches, total),
        "evidence_alignment": ratio(evidence_hits, evidence_total),
        "violation_free": len(violations) == 0,
        **feature_map,
    }


def _decision_slot(
    value: object,
    *,
    field_name: str,
    strict: bool,
) -> dict[str, object]:
    mapping = object_mapping(value, field_name=field_name)
    status = str(mapping.get("s", ""))
    if status not in {"a", "u", "c"}:
        if strict:
            raise TypeError(f"{field_name}.s must be one of a, u, c")
        return {
            "s": "__invalid__",
            "v": mapping.get("v"),
        }
    return {
        "s": status,
        "v": mapping.get("v"),
    }


def _has_evidence(value: object) -> bool:
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, Mapping):
        return len(value) > 0
    if isinstance(value, list):
        return len(value) > 0
    return value not in (None, False)
