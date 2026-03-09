from __future__ import annotations

from dataclasses import dataclass

from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.calibrator import score_feature


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


def compare_run(run: RunArtifact, profiles: list[ProfileArtifact]) -> ComparisonResult:
    scored_profiles = []

    for profile in profiles:
        overall, prompt_scores = score_run_against_profile(run, profile)
        scored_profiles.append((profile.model_id, overall, prompt_scores))

    ranked = sorted(scored_profiles, key=lambda item: (-item[1], item[0]))
    top1_model, top1_similarity, _ = ranked[0]
    top2_model, top2_similarity, _ = ranked[1]
    claimed_similarity = next(
        (similarity for model_id, similarity, _ in ranked if model_id == run.claimed_model),
        None,
    )

    return ComparisonResult(
        top1_model=top1_model,
        top1_similarity=top1_similarity,
        top2_model=top2_model,
        top2_similarity=top2_similarity,
        margin=top1_similarity - top2_similarity,
        claimed_model=run.claimed_model,
        claimed_model_similarity=claimed_similarity,
        consistency=compute_consistency(run, ranked, top1_model),
    )


def score_run_against_profile(
    run: RunArtifact,
    profile: ProfileArtifact,
) -> tuple[float, dict[str, float]]:
    profile_prompts = {prompt.prompt_id: prompt for prompt in profile.prompts}
    prompt_scores: dict[str, float] = {}

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
            prompt_scores[prompt.prompt_id] = sum(feature_scores) / len(feature_scores)

    overall = sum(prompt_scores.values()) / len(prompt_scores)
    return overall, prompt_scores


def compute_consistency(
    run: RunArtifact,
    ranked_profiles: list[tuple[str, float, dict[str, float]]],
    top1_model: str,
) -> float:
    agreeing_prompts = 0

    for prompt in run.prompts:
        best_model = max(
            ranked_profiles,
            key=lambda item: (item[2].get(prompt.prompt_id, 0.0), item[0]),
        )[0]
        if best_model == top1_model:
            agreeing_prompts += 1

    return agreeing_prompts / max(len(run.prompts), 1)
