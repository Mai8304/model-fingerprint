from __future__ import annotations

import json

from modelfingerprint.extractors.base import FeatureMap


def extract_retrieval(raw_output: str) -> FeatureMap:
    payload = json.loads(raw_output)
    expected = list(payload.get("expected_needles", []))
    found = list(payload.get("found_needles", []))
    expected_set = set(expected)
    hits_in_found_order = [needle for needle in found if needle in expected_set]
    wrong_needles = [needle for needle in found if needle not in expected_set]

    return {
        "needle_hit_count": len(hits_in_found_order),
        "wrong_needle_type": len(wrong_needles),
        "order_preservation": hits_in_found_order == [needle for needle in expected if needle in found],
        "confusion_pattern": ",".join(wrong_needles),
        "position_sensitivity": len(hits_in_found_order) / max(len(expected), 1),
    }
