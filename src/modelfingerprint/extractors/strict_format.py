from __future__ import annotations

import json
import re

from modelfingerprint.extractors.base import FeatureMap


def extract_strict_format(raw_output: str) -> FeatureMap:
    stripped = raw_output.strip()
    parsed_exact = _parse_object(stripped)
    candidate = _extract_candidate_object(stripped)
    parsed_candidate = _parse_object(candidate) if candidate is not None else None

    return {
        "valid_format": parsed_exact is not None,
        "has_extra_text": candidate is not None and candidate != stripped,
        "field_order_match": _field_order_matches(parsed_candidate),
        "constraint_retention": parsed_exact is not None and candidate == stripped,
    }


def _extract_candidate_object(text: str) -> str | None:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match is None:
        return None
    return match.group(0)


def _parse_object(text: str | None) -> dict[str, object] | None:
    if text is None:
        return None

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    return parsed


def _field_order_matches(payload: dict[str, object] | None) -> bool:
    if payload is None:
        return False

    keys = list(payload)
    return keys == sorted(keys)
