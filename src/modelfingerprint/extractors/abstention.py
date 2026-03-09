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
