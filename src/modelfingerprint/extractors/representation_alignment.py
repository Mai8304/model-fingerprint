from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.extractors._v2_helpers import (
    object_mapping,
    prompt_reference,
    ratio,
    require_payload,
    string_list,
)
from modelfingerprint.extractors._v3_helpers import (
    shared_task_result,
    shared_violations,
)
from modelfingerprint.extractors.base import FeatureMap


def extract_representation_alignment(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="representation_alignment_v1")
    canonical_entities = string_list(
        payload.get("canonical_entities", []),
        field_name="canonical_entities",
    )
    alias_map = object_mapping(payload.get("alias_map", {}), field_name="alias_map")
    ambiguous_mentions = string_list(
        payload.get("ambiguous_mentions", []),
        field_name="ambiguous_mentions",
    )
    violations = string_list(payload.get("violations", []), field_name="violations")

    return {
        "canonical_count": len(canonical_entities),
        "alias_count": len(alias_map),
        "ambiguous_count": len(ambiguous_mentions),
        "violation_count": len(violations),
    }


def score_representation_alignment(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("representation_alignment_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="representation_alignment_score_v1")
    canonical_entities = string_list(
        payload.get("canonical_entities", []),
        field_name="canonical_entities",
    )
    alias_map = object_mapping(payload.get("alias_map", {}), field_name="alias_map")
    ambiguous_mentions = string_list(
        payload.get("ambiguous_mentions", []),
        field_name="ambiguous_mentions",
    )
    violations = string_list(payload.get("violations", []), field_name="violations")

    expected_entities = string_list(
        prompt_reference(prompt, key="expected_canonical_entities"),
        field_name="expected_canonical_entities",
    )
    expected_alias_map = object_mapping(
        prompt_reference(prompt, key="expected_alias_map"),
        field_name="expected_alias_map",
    )
    expected_ambiguous = string_list(
        prompt_reference(prompt, key="expected_ambiguous_mentions"),
        field_name="expected_ambiguous_mentions",
    )

    entity_hits = sum(entity in canonical_entities for entity in expected_entities)
    alias_hits = sum(alias_map.get(alias) == target for alias, target in expected_alias_map.items())
    ambiguity_hits = sum(item in ambiguous_mentions for item in expected_ambiguous)

    return {
        "canonical_accuracy": ratio(entity_hits, len(expected_entities)),
        "alias_accuracy": ratio(alias_hits, len(expected_alias_map)),
        "ambiguity_preservation": ratio(ambiguity_hits, len(expected_ambiguous)),
        "violation_free": len(violations) == 0,
    }


def extract_representation_alignment_v3(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="representation_alignment_v3")
    task_result = shared_task_result(payload)
    violations = shared_violations(payload)
    canonical_entities = _string_list_or_mapping_keys(
        task_result.get("canonical_entities", []),
        field_name="task_result.canonical_entities",
    )
    alias_map = object_mapping(task_result.get("alias_map", {}), field_name="task_result.alias_map")
    ambiguous_mentions = _string_list_or_mapping_keys(
        task_result.get("ambiguous_mentions", []),
        field_name="task_result.ambiguous_mentions",
    )
    rejected_items = _string_list_or_mapping_keys(
        task_result.get("rejected_items", []),
        field_name="task_result.rejected_items",
    )

    return {
        "canonical_count": len(canonical_entities),
        "alias_count": len(alias_map),
        "ambiguous_count": len(ambiguous_mentions),
        "rejected_count": len(rejected_items),
        "violation_count": len(violations),
    }


def score_representation_alignment_v3(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("representation_alignment_score_v3 expects PromptDefinition input")
    payload = require_payload(
        canonical_output,
        extractor_name="representation_alignment_score_v3",
    )
    task_result = shared_task_result(payload)
    violations = shared_violations(payload)

    canonical_entities = _string_list_or_mapping_keys(
        task_result.get("canonical_entities", []),
        field_name="task_result.canonical_entities",
    )
    alias_map = object_mapping(task_result.get("alias_map", {}), field_name="task_result.alias_map")
    ambiguous_mentions = _string_list_or_mapping_keys(
        task_result.get("ambiguous_mentions", []),
        field_name="task_result.ambiguous_mentions",
    )
    rejected_items = _string_list_or_mapping_keys(
        task_result.get("rejected_items", []),
        field_name="task_result.rejected_items",
    )

    expected_task_result = object_mapping(
        prompt_reference(prompt, key="expected_task_result"),
        field_name="expected_task_result",
    )
    expected_entities = string_list(
        expected_task_result.get("canonical_entities", []),
        field_name="expected_task_result.canonical_entities",
    )
    expected_alias_map = object_mapping(
        expected_task_result.get("alias_map", {}),
        field_name="expected_task_result.alias_map",
    )
    expected_ambiguous = string_list(
        expected_task_result.get("ambiguous_mentions", []),
        field_name="expected_task_result.ambiguous_mentions",
    )
    expected_rejected = string_list(
        expected_task_result.get("rejected_items", []),
        field_name="expected_task_result.rejected_items",
    )

    entity_hits = sum(entity in canonical_entities for entity in expected_entities)
    alias_hits = sum(alias_map.get(alias) == target for alias, target in expected_alias_map.items())
    ambiguity_hits = sum(item in ambiguous_mentions for item in expected_ambiguous)
    rejected_hits = sum(item in rejected_items for item in expected_rejected)

    return {
        "canonical_accuracy": ratio(entity_hits, len(expected_entities)),
        "alias_accuracy": ratio(alias_hits, len(expected_alias_map)),
        "ambiguity_preservation": ratio(ambiguity_hits, len(expected_ambiguous)),
        "rejection_accuracy": ratio(rejected_hits, len(expected_rejected)),
        "violation_free": len(violations) == 0,
    }


def _string_list_or_mapping_keys(value: object, *, field_name: str) -> list[str]:
    if isinstance(value, Mapping):
        return [str(key) for key in value.keys()]
    return string_list(value, field_name=field_name)
