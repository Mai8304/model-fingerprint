from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Literal

from modelfingerprint.contracts.calibration import (
    CalibrationArtifact,
    CalibrationThresholds,
    CoverageThresholds,
    SimilarityStats,
)
from modelfingerprint.contracts.profile import (
    BooleanFeatureSummary,
    EnumFeatureSummary,
    NumericFeatureSummary,
    ProfileArtifact,
)
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.storage.filesystem import ensure_directories

CHANNEL_WEIGHTS = {
    "score": 0.45,
    "answer": 0.25,
    "reasoning": 0.1,
    "transport": 0.1,
    "surface": 0.1,
}
COMPARISON_DIMENSION_WEIGHTS = {
    "content": 0.7,
    "capability": 0.3,
}
CAPABILITY_WEIGHTS = {
    "thinking": 0.30,
    "tools": 0.25,
    "streaming": 0.15,
    "image_generation": 0.15,
    "vision_understanding": 0.15,
}
IDENTITY_EXCLUDED_FEATURES = frozenset(
    {
        "transport.latency_bucket_ms",
        "transport.reasoning_tokens",
        "transport.finish_reason",
        "surface.field_order_match",
        "surface.had_markdown_fence",
        "surface.key_alias_normalized",
    }
)
CAPABILITY_MATCH_SCORES: dict[str, dict[str, float]] = {
    "supported": {
        "supported": 1.0,
        "accepted_but_ignored": 0.55,
        "unsupported": 0.0,
    },
    "accepted_but_ignored": {
        "supported": 0.75,
        "accepted_but_ignored": 1.0,
        "unsupported": 0.35,
    },
    "unsupported": {
        "supported": 0.35,
        "accepted_but_ignored": 0.55,
        "unsupported": 1.0,
    },
}
ProtocolStatus = Literal["compatible", "insufficient_evidence", "incompatible_protocol"]


@dataclass(frozen=True)
class ProfileMatchScore:
    model_id: str
    overall_similarity: float
    content_similarity: float | None
    prompt_scores: dict[str, float]
    capability_similarity: float | None
    answer_similarity: float | None
    reasoning_similarity: float | None
    transport_similarity: float | None
    surface_similarity: float | None
    answer_coverage_ratio: float
    reasoning_coverage_ratio: float
    capability_coverage_ratio: float
    protocol_status: ProtocolStatus
    protocol_issues: tuple[str, ...]
    hard_mismatches: tuple[str, ...]
    consistency: float


class Calibrator:
    def __init__(self, paths: RepositoryPaths) -> None:
        self._paths = paths

    def calibrate(
        self,
        runs: list[RunArtifact],
        profiles: list[ProfileArtifact],
    ) -> CalibrationArtifact:
        suite_ids = {run.suite_id for run in runs} | {profile.suite_id for profile in profiles}
        if len(suite_ids) != 1:
            raise ValueError("calibration runs and profiles must belong to the same suite")

        same_model_scores: list[float] = []
        cross_model_scores: list[float] = []
        consistency_scores: list[float] = []
        answer_coverages = [
            run.answer_coverage_ratio
            if run.answer_coverage_ratio is not None
            else derive_answer_coverage(run)
            for run in runs
        ]
        reasoning_coverages = [
            run.reasoning_coverage_ratio
            if run.reasoning_coverage_ratio is not None
            else derive_reasoning_coverage(run)
            for run in runs
        ]

        for run in runs:
            for profile in profiles:
                score = score_run_against_profile(run, profile)
                if profile.model_id == (run.claimed_model or run.target_label):
                    same_model_scores.append(score.overall_similarity)
                    consistency_scores.append(score.consistency)
                else:
                    cross_model_scores.append(score.overall_similarity)

        same_stats = build_stats(same_model_scores)
        cross_stats = build_stats(cross_model_scores)
        consistency_stats = build_stats(consistency_scores)
        thresholds = _derive_thresholds(
            same_stats=same_stats,
            cross_stats=cross_stats,
            consistency_stats=consistency_stats,
        )

        return CalibrationArtifact(
            suite_id=next(iter(suite_ids)),
            thresholds=thresholds,
            coverage_thresholds=CoverageThresholds(
                answer_min=percentile(sorted(answer_coverages), 0.05),
                reasoning_min=percentile(sorted(reasoning_coverages), 0.05),
            ),
            same_model_stats=same_stats,
            cross_model_stats=cross_stats,
            protocol_expectations=_merge_protocol_expectations(profiles, runs),
        )

    def write(self, artifact: CalibrationArtifact) -> Path:
        ensure_directories(self._paths.calibration_dir)
        output_path = self._paths.calibration_dir / f"{artifact.suite_id}.json"
        output_path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path


def _derive_thresholds(
    *,
    same_stats: SimilarityStats,
    cross_stats: SimilarityStats,
    consistency_stats: SimilarityStats,
) -> CalibrationThresholds:
    match = same_stats.p05
    unknown = min(cross_stats.p95, match)
    suspicious = max(
        unknown,
        min(match, (match + cross_stats.p95) / 2),
    )
    return CalibrationThresholds(
        match=match,
        suspicious=suspicious,
        unknown=unknown,
        margin=max(0.01, match - suspicious),
        consistency=consistency_stats.p05,
    )


def score_run_against_profile(run: RunArtifact, profile: ProfileArtifact) -> ProfileMatchScore:
    profile_prompts = {prompt.prompt_id: prompt for prompt in profile.prompts}
    prompt_scores: dict[str, float] = {}
    channel_weighted_scores: dict[str, float] = {channel: 0.0 for channel in CHANNEL_WEIGHTS}
    channel_weight_totals: dict[str, float] = {channel: 0.0 for channel in CHANNEL_WEIGHTS}
    prompt_weighted_total = 0.0
    prompt_weight_sum = 0.0
    consistency_weight = 0.0

    for prompt in run.prompts:
        profile_prompt = profile_prompts.get(prompt.prompt_id)
        if profile_prompt is None:
            continue

        channel_scores = _score_prompt_channels(prompt.features, profile_prompt.features)
        if not channel_scores:
            continue

        prompt_score = weighted_average(channel_scores, CHANNEL_WEIGHTS)
        prompt_scores[prompt.prompt_id] = prompt_score
        prompt_weighted_total += prompt_score * profile_prompt.weight
        prompt_weight_sum += profile_prompt.weight
        if prompt_score >= 0.5:
            consistency_weight += profile_prompt.weight

        for channel, channel_score in channel_scores.items():
            channel_weighted_scores[channel] += channel_score * profile_prompt.weight
            channel_weight_totals[channel] += profile_prompt.weight

    content_similarity = (
        0.0 if prompt_weight_sum == 0 else prompt_weighted_total / prompt_weight_sum
    )
    consistency = 0.0 if prompt_weight_sum == 0 else consistency_weight / prompt_weight_sum
    answer_coverage_ratio = (
        run.answer_coverage_ratio
        if run.answer_coverage_ratio is not None
        else derive_answer_coverage(run)
    )
    reasoning_coverage_ratio = (
        run.reasoning_coverage_ratio
        if run.reasoning_coverage_ratio is not None
        else derive_reasoning_coverage(run)
    )
    protocol_status, protocol_issues = determine_protocol_status(
        run=run,
        profile=profile,
        answer_coverage_ratio=answer_coverage_ratio,
        reasoning_coverage_ratio=reasoning_coverage_ratio,
    )
    (
        capability_similarity,
        capability_coverage_ratio,
        hard_mismatches,
    ) = _score_capability_dimension(run, profile)
    overall = _combine_dimension_scores(
        content_similarity=content_similarity,
        capability_similarity=capability_similarity,
    )
    return ProfileMatchScore(
        model_id=profile.model_id,
        overall_similarity=overall,
        content_similarity=content_similarity,
        prompt_scores=prompt_scores,
        capability_similarity=capability_similarity,
        answer_similarity=_channel_similarity(
            "answer",
            channel_weighted_scores,
            channel_weight_totals,
        ),
        reasoning_similarity=_channel_similarity(
            "reasoning",
            channel_weighted_scores,
            channel_weight_totals,
        ),
        transport_similarity=_channel_similarity(
            "transport",
            channel_weighted_scores,
            channel_weight_totals,
        ),
        surface_similarity=_channel_similarity(
            "surface",
            channel_weighted_scores,
            channel_weight_totals,
        ),
        answer_coverage_ratio=answer_coverage_ratio,
        reasoning_coverage_ratio=reasoning_coverage_ratio,
        capability_coverage_ratio=capability_coverage_ratio,
        protocol_status=protocol_status,
        protocol_issues=tuple(protocol_issues),
        hard_mismatches=hard_mismatches,
        consistency=consistency,
    )


def score_feature(
    value: object,
    summary: NumericFeatureSummary | BooleanFeatureSummary | EnumFeatureSummary,
) -> float:
    if isinstance(summary, NumericFeatureSummary):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("numeric summary requires numeric values")
        observed = float(value)
        scale = summary.mad or 1.0
        return 1.0 / (1.0 + abs(observed - summary.median) / scale)

    if isinstance(summary, BooleanFeatureSummary):
        return summary.p_true if value is True else 1.0 - summary.p_true

    return summary.distribution.get(str(value), 0.0)


def build_stats(values: list[float]) -> SimilarityStats:
    if not values:
        raise ValueError("at least one score is required")

    ordered = sorted(values)
    return SimilarityStats(
        mean=mean(ordered),
        p05=percentile(ordered, 0.05),
        p50=percentile(ordered, 0.50),
        p95=percentile(ordered, 0.95),
    )


def percentile(values: list[float], fraction: float) -> float:
    if len(values) == 1:
        return values[0]

    index = round((len(values) - 1) * fraction)
    return values[index]


def derive_answer_coverage(run: RunArtifact) -> float:
    if not run.prompts:
        return 0.0
    return sum(
        prompt.status == "completed" and prompt.raw_output is not None for prompt in run.prompts
    ) / len(run.prompts)


def derive_reasoning_coverage(run: RunArtifact) -> float:
    if not run.prompts:
        return 0.0
    visible_count = 0
    for prompt in run.prompts:
        if prompt.completion is not None and prompt.completion.reasoning_visible:
            visible_count += 1
        elif prompt.features.get("transport.reasoning_visible") is True:
            visible_count += 1
    return visible_count / len(run.prompts)


def weighted_average(values: dict[str, float], weights: dict[str, float]) -> float:
    total_weight = sum(weights.get(channel, 0.0) for channel in values)
    if total_weight == 0.0:
        return 0.0
    return sum(values[channel] * weights.get(channel, 0.0) for channel in values) / total_weight


def _score_prompt_channels(
    run_features: Mapping[str, object],
    profile_features: dict[str, NumericFeatureSummary | BooleanFeatureSummary | EnumFeatureSummary],
) -> dict[str, float]:
    channel_feature_scores: dict[str, list[float]] = {}
    for feature_name, summary in profile_features.items():
        if feature_name in IDENTITY_EXCLUDED_FEATURES:
            continue
        if feature_name not in run_features:
            continue
        channel = feature_name.split(".", 1)[0]
        channel_feature_scores.setdefault(channel, []).append(
            score_feature(run_features[feature_name], summary)
        )
    return {
        channel: sum(scores) / len(scores)
        for channel, scores in channel_feature_scores.items()
        if scores
    }


def _channel_similarity(
    channel: str,
    weighted_scores: dict[str, float],
    weight_totals: dict[str, float],
) -> float | None:
    total = weight_totals[channel]
    if total == 0.0:
        return None
    return weighted_scores[channel] / total


def determine_protocol_status(
    *,
    run: RunArtifact,
    profile: ProfileArtifact,
    answer_coverage_ratio: float,
    reasoning_coverage_ratio: float,
) -> tuple[ProtocolStatus, list[str]]:
    issues: list[str] = []
    if run.protocol_compatibility is not None:
        issues.extend(run.protocol_compatibility.issues)
        if run.protocol_compatibility.satisfied is False:
            return "incompatible_protocol", issues

    if any(prompt.status == "unsupported_capability" for prompt in run.prompts):
        issues.append("run contains unsupported capability prompts")
        return "incompatible_protocol", issues

    expected_reasoning = profile.reasoning_coverage_ratio or 0.0
    if expected_reasoning >= 0.5 and reasoning_coverage_ratio < max(0.5, expected_reasoning * 0.8):
        issues.append("reasoning coverage is below the profile expectation")
        return "incompatible_protocol", issues

    if answer_coverage_ratio == 0.0:
        issues.append("answer coverage is zero")
        return "insufficient_evidence", issues

    return "compatible", issues


def _score_capability_dimension(
    run: RunArtifact,
    profile: ProfileArtifact,
) -> tuple[float | None, float, tuple[str, ...]]:
    if run.capability_probe is None or profile.capability_profile is None:
        return None, 0.0, ()

    total_weight = 0.0
    scored_weight = 0.0
    weighted_score = 0.0
    hard_mismatches: list[str] = []

    for capability, summary in profile.capability_profile.capabilities.items():
        capability_weight = CAPABILITY_WEIGHTS.get(capability, 0.0)
        if capability_weight == 0.0:
            continue
        total_weight += capability_weight

        outcome = run.capability_probe.capabilities.get(capability)
        if outcome is None or outcome.status == "insufficient_evidence":
            continue

        reference_distribution = {
            status: probability
            for status, probability in summary.distribution.items()
            if status != "insufficient_evidence"
        }
        reference_mass = sum(reference_distribution.values())
        if reference_mass <= 0.0:
            continue

        normalized_distribution = {
            status: probability / reference_mass
            for status, probability in reference_distribution.items()
        }
        capability_score = 0.0
        for reference_status, probability in normalized_distribution.items():
            capability_score += probability * CAPABILITY_MATCH_SCORES.get(reference_status, {}).get(
                outcome.status,
                0.0,
            )

        weighted_score += capability_score * capability_weight
        scored_weight += capability_weight

        if (
            capability in {"thinking", "tools"}
            and summary.distribution.get("supported", 0.0) >= 0.8
            and outcome.status == "unsupported"
        ):
            hard_mismatches.append(capability)

    if total_weight == 0.0:
        return None, 0.0, tuple(sorted(set(hard_mismatches)))
    if scored_weight == 0.0:
        return None, 0.0, tuple(sorted(set(hard_mismatches)))

    return (
        weighted_score / scored_weight,
        scored_weight / total_weight,
        tuple(sorted(set(hard_mismatches))),
    )


def _combine_dimension_scores(
    *,
    content_similarity: float | None,
    capability_similarity: float | None,
) -> float:
    weighted_total = 0.0
    weight_sum = 0.0
    if content_similarity is not None:
        weighted_total += content_similarity * COMPARISON_DIMENSION_WEIGHTS["content"]
        weight_sum += COMPARISON_DIMENSION_WEIGHTS["content"]
    if capability_similarity is not None:
        weighted_total += capability_similarity * COMPARISON_DIMENSION_WEIGHTS["capability"]
        weight_sum += COMPARISON_DIMENSION_WEIGHTS["capability"]
    if weight_sum == 0.0:
        return 0.0
    return weighted_total / weight_sum


def _merge_protocol_expectations(
    profiles: list[ProfileArtifact],
    runs: list[RunArtifact],
) -> dict[str, object] | None:
    payloads: list[dict[str, object]] = []
    payloads.extend(
        profile.protocol_expectations
        for profile in profiles
        if profile.protocol_expectations is not None
    )
    payloads.extend(
        {
            "satisfied": payload.satisfied,
            "required_capabilities": payload.required_capabilities,
            "issues": payload.issues,
        }
        for run in runs
        for payload in [run.protocol_compatibility]
        if payload is not None
    )
    if not payloads:
        return None

    required_capabilities = sorted(
        {
            capability
            for payload in payloads
            for capability in _string_list(payload.get("required_capabilities"))
            if isinstance(capability, str)
        }
    )
    issues = sorted(
        {
            issue
            for payload in payloads
            for issue in _string_list(payload.get("issues"))
            if isinstance(issue, str)
        }
    )
    return {
        "satisfied": all(payload.get("satisfied") is True for payload in payloads),
        "required_capabilities": required_capabilities,
        "issues": issues,
    }


def _string_list(value: object | None) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
