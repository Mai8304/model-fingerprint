from __future__ import annotations

import json
import re
from collections.abc import Mapping

from modelfingerprint.canonicalizers._common import strip_markdown_fence
from modelfingerprint.extractors.base import FeatureMap, SurfaceExtractorInput

EXPECTED_FIELD_ORDER = {
    "strict_json_v2": ["answer", "confidence"],
    "tolerant_json_v3": ["task_result", "evidence", "unknowns", "violations"],
    "structured_extraction_v2": ["requested_fields", "extracted", "evidence", "hallucinated"],
    "retrieval_v2": ["expected_needles", "found_needles"],
}

TAG_PATTERN = re.compile(r"<(?P<tag>status|reason)>(?P<value>.*?)</(?P=tag)>", re.DOTALL)


def extract_surface_contract(surface_input: object) -> FeatureMap:
    if not isinstance(surface_input, SurfaceExtractorInput):
        raise TypeError("surface_contract_v1 expects SurfaceExtractorInput input")

    raw_output = surface_input.raw_output.strip()
    format_id = surface_input.canonical_output.format_id
    event_codes = {event.code for event in surface_input.canonicalization_events}
    had_markdown_fence = "```" in raw_output
    unfenced_output, _ = strip_markdown_fence(raw_output)

    if format_id in EXPECTED_FIELD_ORDER:
        has_extra_text = _has_extra_json_text(unfenced_output)
        field_order_match = _json_field_order_matches(
            unfenced_output,
            EXPECTED_FIELD_ORDER[format_id],
        )
    elif format_id == "tagged_text_v2":
        has_extra_text = _has_extra_tagged_text(unfenced_output)
        field_order_match = _tag_order_matches(unfenced_output, ["status", "reason"])
    else:
        has_extra_text = False
        field_order_match = True

    constraint_retention = not had_markdown_fence and not has_extra_text and field_order_match
    return {
        "had_markdown_fence": had_markdown_fence,
        "has_extra_text": has_extra_text,
        "parse_repaired": len(surface_input.canonicalization_events) > 0,
        "repair_event_count": len(surface_input.canonicalization_events),
        "has_extra_prefix_text": "stripped_prefix_text" in event_codes,
        "has_extra_suffix_text": "stripped_suffix_text" in event_codes,
        "key_alias_normalized": "normalized_key_alias" in event_codes,
        "field_order_match": field_order_match,
        "constraint_retention": constraint_retention,
    }


def _has_extra_json_text(text: str) -> bool:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match is None:
        return True
    return text.strip() != match.group(0).strip()


def _json_field_order_matches(text: str, expected_keys: list[str]) -> bool:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match is None:
        return False
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return False
    if not isinstance(payload, Mapping):
        return False
    return list(payload) == expected_keys


def _has_extra_tagged_text(text: str) -> bool:
    remainder = text
    for match in TAG_PATTERN.finditer(text):
        remainder = remainder.replace(match.group(0), "", 1)
    return remainder.strip() != ""


def _tag_order_matches(text: str, expected_tags: list[str]) -> bool:
    tags = [match.group("tag") for match in TAG_PATTERN.finditer(text)]
    return tags == expected_tags
