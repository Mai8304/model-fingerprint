from __future__ import annotations

from typing import Literal

from modelfingerprint.contracts.calibration import CalibrationThresholds
from modelfingerprint.services.comparator import ComparisonResult

Verdict = Literal["match", "suspicious", "mismatch", "unknown"]


def decide_verdict(result: ComparisonResult, thresholds: CalibrationThresholds) -> Verdict:
    if result.top1_similarity < thresholds.unknown:
        return "unknown"

    if (
        result.claimed_model is not None
        and result.top1_model == result.claimed_model
        and result.top1_similarity >= thresholds.match
        and result.margin >= thresholds.margin
        and result.consistency >= thresholds.consistency
    ):
        return "match"

    if (
        result.claimed_model is not None
        and result.top1_model != result.claimed_model
        and result.top1_similarity >= thresholds.suspicious
        and result.margin >= thresholds.margin
        and (result.claimed_model_similarity or 0.0) < thresholds.unknown
    ):
        return "mismatch"

    return "suspicious"
