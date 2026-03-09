from __future__ import annotations

import json

from modelfingerprint.extractors.base import FeatureMap


def extract_structured_extraction(raw_output: str) -> FeatureMap:
    payload = json.loads(raw_output)
    requested_fields = list(payload.get("requested_fields", []))
    extracted_fields = dict(payload.get("extracted", {}))
    evidence_fields = set(payload.get("evidence", []))
    hallucinated_fields = list(payload.get("hallucinated", []))

    requested = set(requested_fields)
    extracted = set(extracted_fields)
    matched = requested & extracted
    missing = sorted(requested - extracted)

    denominator = max(len(requested_fields), 1)

    return {
        "field_accuracy": len(matched) / denominator,
        "evidence_alignment": len(matched & evidence_fields) / denominator,
        "hallucinated_fields": len(hallucinated_fields),
        "missing_field_pattern": ",".join(missing),
    }
