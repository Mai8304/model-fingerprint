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


def extract_context_retrieval(canonical_output: object) -> FeatureMap:
    payload = require_payload(canonical_output, extractor_name="context_retrieval_v1")
    found_entities = string_list(payload.get("found_entities", []), field_name="found_entities")
    paragraph_map = object_mapping(payload.get("paragraph_map", {}), field_name="paragraph_map")
    excluded_entities = string_list(
        payload.get("excluded_entities", []),
        field_name="excluded_entities",
    )
    confusions = string_list(payload.get("confusions", []), field_name="confusions")

    return {
        "found_count": len(found_entities),
        "excluded_count": len(excluded_entities),
        "confusion_count": len(confusions),
        "paragraph_annotation_rate": ratio(len(paragraph_map), len(found_entities)),
    }


def score_context_retrieval(prompt: object, canonical_output: object) -> FeatureMap:
    if not isinstance(prompt, PromptDefinition):
        raise TypeError("context_retrieval_score_v1 expects PromptDefinition input")
    payload = require_payload(canonical_output, extractor_name="context_retrieval_score_v1")
    found_entities = string_list(payload.get("found_entities", []), field_name="found_entities")
    paragraph_map = object_mapping(payload.get("paragraph_map", {}), field_name="paragraph_map")
    confusions = string_list(payload.get("confusions", []), field_name="confusions")
    expected_entities = string_list(
        prompt_reference(prompt, key="expected_found_entities"),
        field_name="expected_found_entities",
    )
    expected_paragraphs = object_mapping(
        prompt_reference(prompt, key="expected_paragraph_map"),
        field_name="expected_paragraph_map",
    )

    entity_hits = sum(entity in found_entities for entity in expected_entities)
    paragraph_hits = sum(
        paragraph_map.get(entity) == expected_paragraphs.get(entity) for entity in expected_entities
    )

    return {
        "entity_recall": ratio(entity_hits, len(expected_entities)),
        "entity_precision": ratio(entity_hits, len(found_entities)),
        "order_accuracy": found_entities == expected_entities,
        "paragraph_accuracy": ratio(paragraph_hits, len(expected_entities)),
        "confusion_free": len(confusions) == 0,
    }
