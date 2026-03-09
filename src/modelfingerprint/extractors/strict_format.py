from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import FeatureMap


def extract_strict_format(canonical_output: object) -> FeatureMap:
    if not isinstance(canonical_output, CanonicalizedOutput):
        raise TypeError("strict_format_v1 expects CanonicalizedOutput input")
    payload = canonical_output.payload
    if not isinstance(payload, Mapping):
        raise TypeError("strict_format canonical payload must be a mapping")

    features: FeatureMap = {"field_count": len(payload)}
    for key in ("answer", "confidence", "status", "reason"):
        value = payload.get(key)
        features[f"{key}_value"] = "" if value is None else str(value)
    return features
