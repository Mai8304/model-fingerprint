from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.contracts._common import ProbeCapabilityStatus
from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.comparison import (
    CandidateComparison,
    CapabilityComparisonBreakdown,
    ComparisonArtifact,
    ComparisonCoverage,
    ComparisonDiagnostics,
    ComparisonDimensions,
    ComparisonSummary,
    ComparisonThresholdsUsed,
    PromptComparisonBreakdown,
)
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.calibrator import CAPABILITY_MATCH_SCORES, CAPABILITY_WEIGHTS
from modelfingerprint.services.comparator import compare_run, rank_run_against_profiles
from modelfingerprint.services.verdicts import decide_verdict


def build_comparison_artifact(
    *,
    run: RunArtifact,
    profiles: list[ProfileArtifact],
    calibration: CalibrationArtifact,
) -> ComparisonArtifact:
    ranked = rank_run_against_profiles(run, profiles)
    comparison = compare_run(run, profiles)
    verdict = decide_verdict(comparison, calibration)
    top_candidate = ranked[0]
    top_profile = next(
        profile for profile in profiles if profile.model_id == top_candidate.model_id
    )
    coverage_thresholds = calibration.coverage_thresholds

    return ComparisonArtifact(
        schema_version="comparison.v1",
        suite_id=run.suite_id,
        run_id=run.run_id,
        target_label=run.target_label,
        claimed_model=run.claimed_model,
        calibration_id=calibration.suite_id,
        summary=ComparisonSummary(
            top1_model=comparison.top1_model,
            top1_similarity=comparison.top1_similarity,
            top2_model=comparison.top2_model,
            top2_similarity=comparison.top2_similarity,
            margin=comparison.margin,
            claimed_model_similarity=comparison.claimed_model_similarity,
            consistency=comparison.consistency,
            verdict=verdict,
        ),
        dimensions=ComparisonDimensions(
            content_similarity=comparison.content_similarity,
            capability_similarity=comparison.capability_similarity,
            answer_similarity=comparison.answer_similarity,
            reasoning_similarity=comparison.reasoning_similarity,
            transport_similarity=comparison.transport_similarity,
            surface_similarity=comparison.surface_similarity,
        ),
        coverage=ComparisonCoverage(
            answer_coverage_ratio=comparison.answer_coverage_ratio,
            reasoning_coverage_ratio=comparison.reasoning_coverage_ratio,
            capability_coverage_ratio=comparison.capability_coverage_ratio,
            protocol_status=comparison.protocol_status,
        ),
        diagnostics=ComparisonDiagnostics(
            protocol_issues=list(comparison.protocol_issues),
            hard_mismatches=list(comparison.hard_mismatches),
        ),
        candidates=[
            CandidateComparison(
                model_id=candidate.model_id,
                overall_similarity=candidate.overall_similarity,
                content_similarity=candidate.content_similarity,
                capability_similarity=candidate.capability_similarity,
                answer_similarity=candidate.answer_similarity,
                reasoning_similarity=candidate.reasoning_similarity,
                transport_similarity=candidate.transport_similarity,
                surface_similarity=candidate.surface_similarity,
                consistency=candidate.consistency,
                answer_coverage_ratio=candidate.answer_coverage_ratio,
                reasoning_coverage_ratio=candidate.reasoning_coverage_ratio,
                capability_coverage_ratio=candidate.capability_coverage_ratio,
                protocol_status=candidate.protocol_status,
                protocol_issues=list(candidate.protocol_issues),
                hard_mismatches=list(candidate.hard_mismatches),
                prompt_scores=candidate.prompt_scores,
            )
            for candidate in ranked
        ],
        prompt_breakdown=_build_prompt_breakdown(run, top_candidate.prompt_scores),
        capability_breakdown=_build_capability_breakdown(run, top_profile),
        thresholds_used=ComparisonThresholdsUsed(
            match=calibration.thresholds.match,
            suspicious=calibration.thresholds.suspicious,
            unknown=calibration.thresholds.unknown,
            margin=calibration.thresholds.margin,
            consistency=calibration.thresholds.consistency,
            answer_min=0.0 if coverage_thresholds is None else coverage_thresholds.answer_min,
            reasoning_min=0.0
            if coverage_thresholds is None
            else coverage_thresholds.reasoning_min,
        ),
    )


def _build_prompt_breakdown(
    run: RunArtifact,
    prompt_scores: dict[str, float],
) -> list[PromptComparisonBreakdown]:
    return [
        PromptComparisonBreakdown(
            prompt_id=prompt.prompt_id,
            status=prompt.status,
            similarity=prompt_scores.get(prompt.prompt_id),
            scoreable=bool(prompt.features),
            error_kind=None if prompt.error is None else prompt.error.kind,
            error_message=None if prompt.error is None else prompt.error.message,
        )
        for prompt in run.prompts
    ]


def _build_capability_breakdown(
    run: RunArtifact,
    profile: ProfileArtifact,
) -> list[CapabilityComparisonBreakdown]:
    if run.capability_probe is None or profile.capability_profile is None:
        return []

    breakdown: list[CapabilityComparisonBreakdown] = []
    for capability, expected in profile.capability_profile.capabilities.items():
        weight = CAPABILITY_WEIGHTS.get(capability, 0.0)
        if weight == 0.0:
            continue
        observed = run.capability_probe.capabilities.get(capability)
        similarity = _capability_similarity(
            observed_status=None if observed is None else observed.status,
            expected_distribution=expected.distribution,
        )
        breakdown.append(
            CapabilityComparisonBreakdown(
                capability=capability,
                weight=weight,
                observed_status=None if observed is None else observed.status,
                expected_distribution=expected.distribution,
                similarity=similarity,
            )
        )
    breakdown.sort(key=lambda item: (-item.weight, item.capability))
    return breakdown


def _capability_similarity(
    *,
    observed_status: str | None,
    expected_distribution: Mapping[ProbeCapabilityStatus, float],
) -> float | None:
    if observed_status is None or observed_status == "insufficient_evidence":
        return None
    reference_distribution = {
        status: probability
        for status, probability in expected_distribution.items()
        if status != "insufficient_evidence"
    }
    reference_mass = sum(reference_distribution.values())
    if reference_mass <= 0.0:
        return None
    normalized_distribution = {
        status: probability / reference_mass
        for status, probability in reference_distribution.items()
    }
    score = 0.0
    observed_status_name = str(observed_status)
    for reference_status, probability in normalized_distribution.items():
        score += probability * CAPABILITY_MATCH_SCORES.get(str(reference_status), {}).get(
            observed_status_name,
            0.0,
        )
    return score
