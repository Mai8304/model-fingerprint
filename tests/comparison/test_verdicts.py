from __future__ import annotations

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.services.comparator import ComparisonResult
from modelfingerprint.services.verdicts import decide_verdict

CALIBRATION = CalibrationArtifact.model_validate(
    {
        "suite_id": "fingerprint-suite-v3",
        "thresholds": {
            "match": 0.8,
            "suspicious": 0.6,
            "unknown": 0.4,
            "margin": 0.1,
            "consistency": 0.7,
        },
        "coverage_thresholds": {
            "answer_min": 0.8,
            "reasoning_min": 0.5,
        },
        "same_model_stats": {
            "mean": 0.9,
            "p05": 0.8,
            "p50": 0.9,
            "p95": 0.98,
        },
        "cross_model_stats": {
            "mean": 0.35,
            "p05": 0.2,
            "p50": 0.33,
            "p95": 0.45,
        },
        "protocol_expectations": {
            "satisfied": True,
            "required_capabilities": ["chat_completions", "visible_reasoning"],
            "issues": [],
        },
    }
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
        "content_similarity": 0.9,
        "capability_similarity": 1.0,
        "answer_similarity": 0.9,
        "reasoning_similarity": 0.9,
        "transport_similarity": 0.9,
        "surface_similarity": 0.9,
        "answer_coverage_ratio": 1.0,
        "reasoning_coverage_ratio": 1.0,
        "capability_coverage_ratio": 1.0,
        "protocol_status": "compatible",
        "protocol_issues": (),
        "hard_mismatches": (),
    }
    payload.update(overrides)
    return ComparisonResult(**payload)


def test_verdicts_emit_match_suspicious_mismatch_and_unknown() -> None:
    assert decide_verdict(build_result(), CALIBRATION) == "match"
    assert (
        decide_verdict(
            build_result(top1_similarity=0.72, margin=0.05, consistency=0.8),
            CALIBRATION,
        )
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
            CALIBRATION,
        )
        == "mismatch"
    )
    assert (
        decide_verdict(
            build_result(top1_similarity=0.2, claimed_model_similarity=0.2),
            CALIBRATION,
        )
        == "unknown"
    )
    assert (
        decide_verdict(
            build_result(answer_coverage_ratio=0.5),
            CALIBRATION,
        )
        == "insufficient_evidence"
    )
    assert (
        decide_verdict(
            build_result(protocol_status="incompatible_protocol"),
            CALIBRATION,
        )
        == "incompatible_protocol"
    )
