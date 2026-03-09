from __future__ import annotations

from collections import defaultdict
from statistics import median

from modelfingerprint.contracts.profile import (
    BooleanFeatureSummary,
    EnumFeatureSummary,
    NumericFeatureSummary,
    ProfileArtifact,
    ProfilePromptSummary,
)
from modelfingerprint.contracts.run import FeaturePrimitive, RunArtifact


class ProfileBuildError(ValueError):
    """Raised when run artifacts cannot be aggregated into a profile."""


def build_profile(
    model_id: str,
    runs: list[RunArtifact],
    prompt_weights: dict[str, float],
) -> ProfileArtifact:
    if not runs:
        raise ProfileBuildError("at least one run is required")

    suite_ids = {run.suite_id for run in runs}
    if len(suite_ids) != 1:
        raise ProfileBuildError("profile runs must all belong to the same suite")

    prompt_feature_values: dict[str, dict[str, list[FeaturePrimitive]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for run in runs:
        for prompt in run.prompts:
            for feature_name, value in prompt.features.items():
                prompt_feature_values[prompt.prompt_id][feature_name].append(value)

    prompts = [
        ProfilePromptSummary(
            prompt_id=prompt_id,
            weight=prompt_weights.get(prompt_id, 1.0),
            features={
                feature_name: summarize_feature(values)
                for feature_name, values in sorted(feature_map.items())
            },
        )
        for prompt_id, feature_map in sorted(prompt_feature_values.items())
    ]

    return ProfileArtifact(
        model_id=model_id,
        suite_id=next(iter(suite_ids)),
        sample_count=len(runs),
        prompts=prompts,
    )


def summarize_feature(values: list[FeaturePrimitive]) -> NumericFeatureSummary | BooleanFeatureSummary | EnumFeatureSummary:
    first = values[0]

    if isinstance(first, bool):
        true_count = sum(value is True for value in values)
        return BooleanFeatureSummary(kind="boolean", p_true=true_count / len(values))

    if isinstance(first, (int, float)) and not isinstance(first, bool):
        numbers = [float(value) for value in values]
        feature_median = median(numbers)
        deviations = [abs(value - feature_median) for value in numbers]
        return NumericFeatureSummary(kind="numeric", median=feature_median, mad=median(deviations))

    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[str(value)] += 1

    total = len(values)
    return EnumFeatureSummary(
        kind="enum",
        distribution={key: count / total for key, count in sorted(counts.items())},
    )
