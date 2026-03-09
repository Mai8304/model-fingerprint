from __future__ import annotations

from collections.abc import Mapping, Sequence

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import FeatureMap


def extract_retrieval(canonical_output: object) -> FeatureMap:
    if not isinstance(canonical_output, CanonicalizedOutput):
        raise TypeError("retrieval_v1 expects CanonicalizedOutput input")
    payload = canonical_output.payload
    if not isinstance(payload, Mapping):
        raise TypeError("retrieval canonical payload must be a mapping")

    expected = _string_list(payload.get("expected_needles", []))
    found = _string_list(payload.get("found_needles", []))
    expected_set = set(expected)
    hits_in_found_order = [needle for needle in found if needle in expected_set]
    wrong_needles = [needle for needle in found if needle not in expected_set]
    expected_hits = [needle for needle in expected if needle in found]

    return {
        "needle_hit_count": len(hits_in_found_order),
        "wrong_needle_type": len(wrong_needles),
        "order_preservation": hits_in_found_order == expected_hits,
        "confusion_pattern": ",".join(wrong_needles),
        "position_sensitivity": len(hits_in_found_order) / max(len(expected), 1),
    }


def _string_list(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [str(item) for item in value]
    raise TypeError("expected a list of strings")
