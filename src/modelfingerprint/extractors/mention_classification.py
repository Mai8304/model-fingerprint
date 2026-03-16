from __future__ import annotations

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.extractors._shared_helpers import (
    object_mapping,
    prompt_reference,
    ratio,
    require_payload,
)
from modelfingerprint.extractors._v3_helpers import (
    shared_task_result,
    shared_violations,
)
from modelfingerprint.extractors.base import FeatureMap


def extract_mention_classification_v1(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="mention_classification_v1")
    task_result = shared_task_result(payload)
    violations = shared_violations(payload)

    canonical = 0
    ambiguous = 0
    rejected = 0
    for value in task_result.values():
        label = _classification_label(value)
        if label.startswith("C:"):
            canonical += 1
        elif label == "M":
            ambiguous += 1
        elif label == "R":
            rejected += 1

    return {
        "canonical_count": canonical,
        "ambiguous_count": ambiguous,
        "rejected_count": rejected,
        "violation_count": len(violations),
    }


def score_mention_classification_v1(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("mention_classification_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="mention_classification_score_v1")
    task_result = shared_task_result(payload)
    violations = shared_violations(payload)
    expected_task_result = object_mapping(
        prompt_reference(prompt, key="expected_task_result"),
        field_name="expected_task_result",
    )

    classification_hits = 0
    ambiguous_hits = 0
    rejected_hits = 0
    threshold_hits = 0
    total = 0
    ambiguous_total = 0
    rejected_total = 0
    threshold_total = 0

    for mention_id, expected_value in expected_task_result.items():
        total += 1
        expected_label = _classification_label(expected_value)
        actual_label = _classification_label(task_result.get(mention_id))
        if actual_label == expected_label:
            classification_hits += 1
        if expected_label == "M":
            ambiguous_total += 1
            if actual_label == "M":
                ambiguous_hits += 1
        if expected_label == "R":
            rejected_total += 1
            if actual_label == "R":
                rejected_hits += 1
        if expected_label in {"M", "R"}:
            threshold_total += 1
            if actual_label == expected_label:
                threshold_hits += 1

    return {
        "classification_accuracy": ratio(classification_hits, total),
        "ambiguity_accuracy": ratio(ambiguous_hits, ambiguous_total),
        "rejection_accuracy": ratio(rejected_hits, rejected_total),
        "threshold_accuracy": ratio(threshold_hits, threshold_total),
        "violation_free": len(violations) == 0,
    }


def _classification_label(value: object) -> str:
    return str(value)
