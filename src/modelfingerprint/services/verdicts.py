from __future__ import annotations

from typing import Literal

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.services.comparator import ComparisonResult

Verdict = Literal[
    "match",
    "suspicious",
    "mismatch",
    "unknown",
    "insufficient_evidence",
    "incompatible_protocol",
]


def decide_verdict(result: ComparisonResult, calibration: CalibrationArtifact) -> Verdict:
    if result.protocol_status == "incompatible_protocol":
        return "incompatible_protocol"

    if (
        result.capability_similarity is not None
        or result.capability_coverage_ratio > 0.0
        or bool(result.hard_mismatches)
    ) and result.capability_coverage_ratio < 0.5:
        return "insufficient_evidence"

    coverage = calibration.coverage_thresholds
    if coverage is not None:
        if result.answer_coverage_ratio < coverage.answer_min:
            return "insufficient_evidence"
        if result.reasoning_coverage_ratio < coverage.reasoning_min:
            return "insufficient_evidence"

    thresholds = calibration.thresholds
    if result.top1_similarity < thresholds.unknown:
        return "unknown"

    if result.hard_mismatches and result.content_similarity is not None:
        if result.content_similarity >= thresholds.suspicious:
            return "suspicious"

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
