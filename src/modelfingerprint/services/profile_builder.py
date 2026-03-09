from __future__ import annotations

from collections import defaultdict
from statistics import mean, median

from modelfingerprint.contracts._common import FeaturePrimitive
from modelfingerprint.contracts.profile import (
    BooleanFeatureSummary,
    EnumFeatureSummary,
    NumericFeatureSummary,
    ProfileArtifact,
    ProfilePromptSummary,
)
from modelfingerprint.contracts.run import RunArtifact


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
    prompt_answer_coverage: dict[str, list[float]] = defaultdict(list)
    prompt_reasoning_coverage: dict[str, list[float]] = defaultdict(list)
    prompt_reasoning_visible: dict[str, list[float]] = defaultdict(list)

    for run in runs:
        for prompt in run.prompts:
            prompt_answer_coverage[prompt.prompt_id].append(
                1.0 if prompt.status == "completed" and prompt.raw_output is not None else 0.0
            )
            reasoning_visible = (
                1.0
                if prompt.completion is not None and prompt.completion.reasoning_visible
                else 0.0
            )
            if prompt.completion is None and "transport.reasoning_visible" in prompt.features:
                reasoning_visible = (
                    1.0 if prompt.features["transport.reasoning_visible"] is True else 0.0
                )
            prompt_reasoning_coverage[prompt.prompt_id].append(reasoning_visible)
            prompt_reasoning_visible[prompt.prompt_id].append(reasoning_visible)
            for feature_name, value in prompt.features.items():
                prompt_feature_values[prompt.prompt_id][feature_name].append(value)

    prompts = [
        ProfilePromptSummary(
            prompt_id=prompt_id,
            weight=prompt_weights.get(prompt_id, 1.0),
            answer_coverage_ratio=mean(prompt_answer_coverage[prompt_id]),
            reasoning_coverage_ratio=mean(prompt_reasoning_coverage[prompt_id]),
            expected_reasoning_visible=mean(prompt_reasoning_visible[prompt_id]),
            features={
                feature_name: summarize_feature(values)
                for feature_name, values in sorted(feature_map.items())
            },
        )
        for prompt_id, feature_map in sorted(prompt_feature_values.items())
    ]

    protocol_expectations = _merge_protocol_expectations(runs)

    return ProfileArtifact(
        model_id=model_id,
        suite_id=next(iter(suite_ids)),
        sample_count=len(runs),
        answer_coverage_ratio=mean(
            [
                run.answer_coverage_ratio
                if run.answer_coverage_ratio is not None
                else _derive_answer_coverage(run)
                for run in runs
            ]
        ),
        reasoning_coverage_ratio=mean(
            [
                run.reasoning_coverage_ratio
                if run.reasoning_coverage_ratio is not None
                else _derive_reasoning_coverage(run)
                for run in runs
            ]
        ),
        protocol_expectations=protocol_expectations,
        prompts=prompts,
    )


def summarize_feature(
    values: list[FeaturePrimitive],
) -> NumericFeatureSummary | BooleanFeatureSummary | EnumFeatureSummary:
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


def _derive_answer_coverage(run: RunArtifact) -> float:
    if not run.prompts:
        return 0.0
    return sum(
        prompt.status == "completed" and prompt.raw_output is not None for prompt in run.prompts
    ) / len(run.prompts)


def _derive_reasoning_coverage(run: RunArtifact) -> float:
    if not run.prompts:
        return 0.0
    visible_count = 0
    for prompt in run.prompts:
        if prompt.completion is not None and prompt.completion.reasoning_visible:
            visible_count += 1
        elif prompt.features.get("transport.reasoning_visible") is True:
            visible_count += 1
    return visible_count / len(run.prompts)


def _merge_protocol_expectations(runs: list[RunArtifact]) -> dict[str, object] | None:
    payloads = [
        run.protocol_compatibility for run in runs if run.protocol_compatibility is not None
    ]
    if not payloads:
        return None

    required_capabilities = sorted(
        {capability for payload in payloads for capability in payload.required_capabilities}
    )
    issues = sorted({issue for payload in payloads for issue in payload.issues})
    return {
        "satisfied": all(payload.satisfied for payload in payloads),
        "required_capabilities": required_capabilities,
        "issues": issues,
    }
