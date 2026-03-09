from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from statistics import mean

from modelfingerprint.contracts.calibration import (
    CalibrationArtifact,
    CalibrationThresholds,
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

        profile_by_model = {profile.model_id: profile for profile in profiles}
        same_model_scores: list[float] = []
        cross_model_scores: list[float] = []
        consistency_scores: list[float] = []

        for run in runs:
            for profile in profiles:
                similarity, consistency = score_run_against_profile(run, profile)
                if profile.model_id == (run.claimed_model or run.target_label):
                    same_model_scores.append(similarity)
                    consistency_scores.append(consistency)
                else:
                    cross_model_scores.append(similarity)

        same_stats = build_stats(same_model_scores)
        cross_stats = build_stats(cross_model_scores)
        consistency_stats = build_stats(consistency_scores)
        suspicious = max(
            cross_stats.p95,
            min(same_stats.p05, (same_stats.p05 + cross_stats.p95) / 2),
        )
        thresholds = CalibrationThresholds(
            match=same_stats.p05,
            suspicious=suspicious,
            unknown=cross_stats.p95,
            margin=max(0.01, same_stats.p05 - suspicious),
            consistency=consistency_stats.p50,
        )

        return CalibrationArtifact(
            suite_id=next(iter(suite_ids)),
            thresholds=thresholds,
            same_model_stats=same_stats,
            cross_model_stats=cross_stats,
        )

    def write(self, artifact: CalibrationArtifact) -> Path:
        ensure_directories(self._paths.calibration_dir)
        output_path = self._paths.calibration_dir / f"{artifact.suite_id}.json"
        output_path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path


def score_run_against_profile(run: RunArtifact, profile: ProfileArtifact) -> tuple[float, float]:
    profile_prompts = {prompt.prompt_id: prompt for prompt in profile.prompts}
    prompt_scores: list[float] = []

    for prompt in run.prompts:
        profile_prompt = profile_prompts.get(prompt.prompt_id)
        if profile_prompt is None:
            continue

        feature_scores = [
            score_feature(prompt.features[name], summary)
            for name, summary in profile_prompt.features.items()
            if name in prompt.features
        ]
        if feature_scores:
            prompt_scores.append(sum(feature_scores) / len(feature_scores))

    overall = sum(prompt_scores) / len(prompt_scores)
    consistency = sum(score >= 0.5 for score in prompt_scores) / len(prompt_scores)
    return overall, consistency


def score_feature(value: object, summary: NumericFeatureSummary | BooleanFeatureSummary | EnumFeatureSummary) -> float:
    if isinstance(summary, NumericFeatureSummary):
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
