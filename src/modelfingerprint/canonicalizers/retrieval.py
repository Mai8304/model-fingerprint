from __future__ import annotations

from collections.abc import Sequence

from modelfingerprint.canonicalizers._common import parse_json_object
from modelfingerprint.canonicalizers.base import CanonicalizationError, CanonicalizerResult
from modelfingerprint.contracts.run import CanonicalizedOutput


def canonicalize_retrieval(raw_output: str) -> CanonicalizerResult:
    payload, events = parse_json_object(raw_output)
    expected_needles = _normalize_string_list(
        payload.get("expected_needles"),
        field_name="expected_needles",
    )
    found_needles = _normalize_string_list(
        payload.get("found_needles"),
        field_name="found_needles",
    )
    return (
        CanonicalizedOutput(
            format_id="retrieval_v2",
            payload={
                "expected_needles": expected_needles,
                "found_needles": found_needles,
            },
        ),
        events,
    )


def _normalize_string_list(value: object, *, field_name: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise CanonicalizationError(
            code=f"invalid_{field_name}",
            message=f"{field_name} must be a list of strings",
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise CanonicalizationError(
                code=f"invalid_{field_name}",
                message=f"{field_name} must be a list of strings",
            )
        result.append(item)
    return result
