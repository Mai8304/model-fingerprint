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


def extract_selection_boundary_v1(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="selection_boundary_v1")
    task_result = shared_task_result(payload)
    violations = shared_violations(payload)

    include_count = 0
    ambiguous_count = 0
    variant_count = 0
    rejected_count = 0
    features: FeatureMap = {}
    for mention_id in sorted(task_result):
        label = _label(task_result.get(mention_id))
        features[f"label_{mention_id}"] = label
        if label == "I":
            include_count += 1
        elif label == "A":
            ambiguous_count += 1
        elif label == "V":
            variant_count += 1
        elif label == "R":
            rejected_count += 1

    features.update(
        {
            "include_count": include_count,
            "ambiguous_count": ambiguous_count,
            "variant_count": variant_count,
            "rejected_count": rejected_count,
            "violation_count": len(violations),
        }
    )
    return features


def score_selection_boundary_v1(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("selection_boundary_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="selection_boundary_score_v1")
    task_result = shared_task_result(payload)
    violations = shared_violations(payload)
    expected_task_result = object_mapping(
        prompt_reference(prompt, key="expected_task_result"),
        field_name="expected_task_result",
    )

    hits = 0
    include_hits = 0
    include_total = 0
    ambiguous_hits = 0
    ambiguous_total = 0
    variant_hits = 0
    variant_total = 0
    rejected_hits = 0
    rejected_total = 0
    features: FeatureMap = {}

    for mention_id, expected in expected_task_result.items():
        expected_label = _label(expected)
        actual_label = _label(task_result.get(mention_id))
        features[f"match_{mention_id}"] = actual_label == expected_label
        if actual_label == expected_label:
            hits += 1
        if expected_label == "I":
            include_total += 1
            if actual_label == "I":
                include_hits += 1
        elif expected_label == "A":
            ambiguous_total += 1
            if actual_label == "A":
                ambiguous_hits += 1
        elif expected_label == "V":
            variant_total += 1
            if actual_label == "V":
                variant_hits += 1
        elif expected_label == "R":
            rejected_total += 1
            if actual_label == "R":
                rejected_hits += 1

    features.update(
        {
            "classification_accuracy": ratio(hits, len(expected_task_result)),
            "selection_accuracy": ratio(include_hits, include_total),
            "ambiguity_accuracy": ratio(ambiguous_hits, ambiguous_total),
            "variant_accuracy": ratio(variant_hits, variant_total),
            "rejection_accuracy": ratio(rejected_hits, rejected_total),
            "violation_free": len(violations) == 0,
        }
    )
    return features


def _label(value: object) -> str:
    return str(value)
