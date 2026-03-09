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
from modelfingerprint.extractors._v3_helpers import (
    shared_evidence,
    shared_task_result,
    shared_violations,
)
from modelfingerprint.extractors.base import FeatureMap


def extract_abstention(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="abstention_v1")
    answers = object_mapping(payload.get("answers", {}), field_name="answers")
    unknowns = string_list(payload.get("unknowns", []), field_name="unknowns")
    evidence = object_mapping(payload.get("evidence", {}), field_name="evidence")
    violations = string_list(payload.get("violations", []), field_name="violations")

    return {
        "answered_count": sum(value is not None for value in answers.values()),
        "unknown_count": len(unknowns),
        "evidence_field_count": evidence_slot_count(evidence),
        "violation_count": len(violations),
    }


def score_abstention(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("abstention_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="abstention_score_v1")
    answers = object_mapping(payload.get("answers", {}), field_name="answers")
    unknowns = set(string_list(payload.get("unknowns", []), field_name="unknowns"))
    evidence = object_mapping(payload.get("evidence", {}), field_name="evidence")
    violations = string_list(payload.get("violations", []), field_name="violations")
    expected_answers = object_mapping(
        prompt_reference(prompt, key="expected_answers"),
        field_name="expected_answers",
    )

    answerable = [name for name, value in expected_answers.items() if value is not None]
    unknown_expected = [name for name, value in expected_answers.items() if value is None]
    correct_answers = sum(answers.get(name) == expected_answers[name] for name in answerable)
    abstention_hits = sum(
        answers.get(name) is None or name in unknowns for name in unknown_expected
    )
    evidence_hits = sum(
        evidence_slot_count({name: evidence.get(name)}) > 0
        for name in answerable
        if answers.get(name) == expected_answers[name]
    )

    return {
        "answer_accuracy": ratio(correct_answers, len(answerable)),
        "abstention_accuracy": ratio(abstention_hits, len(unknown_expected)),
        "evidence_alignment": ratio(evidence_hits, len(answerable)),
        "violation_free": len(violations) == 0,
    }


def extract_abstention_v3(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="abstention_v3")
    task_result = shared_task_result(payload)
    evidence = shared_evidence(payload)
    violations = shared_violations(payload)

    statuses = _status_mapping(task_result)
    return {
        "answered_count": sum(status == "answer" for status in statuses.values()),
        "unknown_count": sum(status == "unknown" for status in statuses.values()),
        "conflict_count": sum(status == "conflict_unresolved" for status in statuses.values()),
        "evidence_field_count": evidence_slot_count(evidence),
        "violation_count": len(violations),
    }


def score_abstention_v3(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("abstention_score_v3 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="abstention_score_v3")
    task_result = shared_task_result(payload)
    evidence = shared_evidence(payload)
    violations = shared_violations(payload)
    expected_task_result = object_mapping(
        prompt_reference(prompt, key="expected_task_result"),
        field_name="expected_task_result",
    )

    answer_expected = [
        name for name, value in expected_task_result.items() if _status(value) == "answer"
    ]
    unknown_expected = [
        name for name, value in expected_task_result.items() if _status(value) == "unknown"
    ]
    conflict_expected = [
        name
        for name, value in expected_task_result.items()
        if _status(value) == "conflict_unresolved"
    ]

    answer_hits = sum(
        _status(task_result.get(name)) == "answer"
        and _value(task_result.get(name)) == _value(expected_task_result.get(name))
        for name in answer_expected
    )
    unknown_hits = sum(_status(task_result.get(name)) == "unknown" for name in unknown_expected)
    conflict_hits = sum(
        _status(task_result.get(name)) == "conflict_unresolved" for name in conflict_expected
    )
    evidence_hits = sum(
        evidence_slot_count({name: evidence.get(name)}) > 0
        for name in answer_expected
        if _status(task_result.get(name)) == "answer"
        and _value(task_result.get(name)) == _value(expected_task_result.get(name))
    )

    return {
        "answer_accuracy": ratio(answer_hits, len(answer_expected)),
        "unknown_accuracy": ratio(unknown_hits, len(unknown_expected)),
        "conflict_accuracy": ratio(conflict_hits, len(conflict_expected)),
        "evidence_alignment": ratio(evidence_hits, len(answer_expected)),
        "violation_free": len(violations) == 0,
    }


def _status_mapping(task_result: dict[str, object]) -> dict[str, str]:
    return {name: _status(value) for name, value in task_result.items()}


def _status(value: object) -> str:
    if isinstance(value, dict):
        status = value.get("status")
        if isinstance(status, str):
            return status
    return "unknown"


def _value(value: object) -> object:
    if isinstance(value, dict):
        return value.get("value")
    return None
