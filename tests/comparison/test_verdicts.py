from __future__ import annotations

from modelfingerprint.contracts.calibration import CalibrationThresholds
from modelfingerprint.services.comparator import ComparisonResult
from modelfingerprint.services.verdicts import decide_verdict


THRESHOLDS = CalibrationThresholds(
    match=0.8,
    suspicious=0.6,
    unknown=0.4,
    margin=0.1,
    consistency=0.7,
)


def build_result(**overrides: object) -> ComparisonResult:
    payload = {
        "top1_model": "gpt-5.3",
        "top1_similarity": 0.9,
        "top2_model": "claude-ops-4.6",
        "top2_similarity": 0.7,
        "margin": 0.2,
        "claimed_model": "gpt-5.3",
        "claimed_model_similarity": 0.9,
        "consistency": 0.9,
    }
    payload.update(overrides)
    return ComparisonResult(**payload)


def test_verdicts_emit_match_suspicious_mismatch_and_unknown() -> None:
    assert decide_verdict(build_result(), THRESHOLDS) == "match"
    assert (
        decide_verdict(build_result(top1_similarity=0.72, margin=0.05, consistency=0.8), THRESHOLDS)
        == "suspicious"
    )
    assert (
        decide_verdict(
            build_result(
                top1_model="claude-ops-4.6",
                claimed_model_similarity=0.35,
                top1_similarity=0.82,
                margin=0.2,
            ),
            THRESHOLDS,
        )
        == "mismatch"
    )
    assert decide_verdict(build_result(top1_similarity=0.2, claimed_model_similarity=0.2), THRESHOLDS) == "unknown"
