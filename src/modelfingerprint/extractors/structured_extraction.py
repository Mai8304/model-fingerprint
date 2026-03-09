from __future__ import annotations

from collections.abc import Mapping, Sequence

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import FeatureMap


def extract_structured_extraction(canonical_output: object) -> FeatureMap:
    if not isinstance(canonical_output, CanonicalizedOutput):
        raise TypeError("structured_extraction_v1 expects CanonicalizedOutput input")
    payload = canonical_output.payload
    if not isinstance(payload, Mapping):
        raise TypeError("structured_extraction canonical payload must be a mapping")

    requested_fields = _string_list(payload.get("requested_fields", []))
    extracted_fields = _string_mapping(payload.get("extracted", {}))
    evidence_fields = set(_string_list(payload.get("evidence_fields", [])))
    hallucinated_fields = _string_list(payload.get("hallucinated", []))

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


def _string_list(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [str(item) for item in value]
    raise TypeError("expected a list of strings")


def _string_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise TypeError("expected a mapping payload")
    return {str(key): str(item) for key, item in value.items()}
