from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.calibrator import ProfileMatchScore, score_run_against_profile

ProtocolStatus = Literal["compatible", "insufficient_evidence", "incompatible_protocol"]


@dataclass(frozen=True)
class ComparisonResult:
    top1_model: str
    top1_similarity: float
    top2_model: str
    top2_similarity: float
    margin: float
    claimed_model: str | None
    claimed_model_similarity: float | None
    consistency: float
    answer_similarity: float | None
    reasoning_similarity: float | None
    transport_similarity: float | None
    surface_similarity: float | None
    answer_coverage_ratio: float
    reasoning_coverage_ratio: float
    protocol_status: ProtocolStatus
    protocol_issues: tuple[str, ...]


def compare_run(run: RunArtifact, profiles: list[ProfileArtifact]) -> ComparisonResult:
    scored_profiles: list[ProfileMatchScore] = []

    for profile in profiles:
        scored_profiles.append(score_run_against_profile(run, profile))

    ranked = sorted(
        scored_profiles,
        key=lambda item: (
            -item.overall_similarity,
            _protocol_rank(item.protocol_status),
            item.model_id,
        ),
    )
    top1 = ranked[0]
    top2 = ranked[1] if len(ranked) > 1 else ranked[0]
    claimed_similarity = next(
        (
            score.overall_similarity
            for score in ranked
            if score.model_id == run.claimed_model
        ),
        None,
    )

    return ComparisonResult(
        top1_model=top1.model_id,
        top1_similarity=top1.overall_similarity,
        top2_model=top2.model_id,
        top2_similarity=top2.overall_similarity,
        margin=top1.overall_similarity - top2.overall_similarity,
        claimed_model=run.claimed_model,
        claimed_model_similarity=claimed_similarity,
        consistency=top1.consistency,
        answer_similarity=top1.answer_similarity,
        reasoning_similarity=top1.reasoning_similarity,
        transport_similarity=top1.transport_similarity,
        surface_similarity=top1.surface_similarity,
        answer_coverage_ratio=top1.answer_coverage_ratio,
        reasoning_coverage_ratio=top1.reasoning_coverage_ratio,
        protocol_status=top1.protocol_status,
        protocol_issues=top1.protocol_issues,
    )


def _protocol_rank(status: ProtocolStatus) -> int:
    if status == "compatible":
        return 0
    if status == "insufficient_evidence":
        return 1
    return 2
