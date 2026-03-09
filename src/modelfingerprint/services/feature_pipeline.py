from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import (
    CanonicalizationEvent,
    CanonicalizedOutput,
    NormalizedCompletion,
    PromptExecutionError,
    PromptRequestSnapshot,
    PromptRunResult,
    RunArtifact,
    UsageMetadata,
)
from modelfingerprint.extractors.base import FeatureMap
from modelfingerprint.extractors.registry import ExtractorRegistry

PromptExecutionStatus = Literal[
    "completed",
    "timeout",
    "transport_error",
    "unsupported_capability",
    "truncated",
    "invalid_response",
    "canonicalization_error",
]


@dataclass(frozen=True)
class PromptExecutionResult:
    prompt: PromptDefinition
    status: PromptExecutionStatus = "completed"
    raw_output: str | None = None
    usage: UsageMetadata | None = None
    request_snapshot: PromptRequestSnapshot | None = None
    completion: NormalizedCompletion | None = None
    canonical_output: CanonicalizedOutput | None = None
    canonicalization_events: list[CanonicalizationEvent] = field(default_factory=list)
    error: PromptExecutionError | None = None


class FeaturePipeline:
    def __init__(self, registry: ExtractorRegistry) -> None:
        self._registry = registry

    def build_run_artifact(
        self,
        run_id: str,
        suite_id: str,
        target_label: str,
        claimed_model: str | None,
        executions: list[PromptExecutionResult],
    ) -> RunArtifact:
        prompt_results: list[PromptRunResult] = []
        prompt_count_total = len(executions)
        prompt_count_completed = 0
        prompt_count_scoreable = 0
        answer_visible_count = 0
        reasoning_visible_count = 0

        for execution in executions:
            features: FeatureMap = {}
            if execution.status == "completed":
                prompt_count_completed += 1
                if execution.raw_output is not None:
                    answer_visible_count += 1
                    features = self._registry.extract(execution.prompt, execution.raw_output)
                    if features:
                        prompt_count_scoreable += 1
                if execution.completion is not None and execution.completion.reasoning_visible:
                    reasoning_visible_count += 1

            prompt_results.append(
                PromptRunResult(
                    status=execution.status,
                    prompt_id=execution.prompt.id,
                    raw_output=execution.raw_output,
                    usage=execution.usage,
                    request_snapshot=execution.request_snapshot,
                    completion=execution.completion,
                    canonical_output=execution.canonical_output,
                    canonicalization_events=execution.canonicalization_events,
                    features=features,
                    error=execution.error,
                )
            )

        return RunArtifact(
            run_id=run_id,
            suite_id=suite_id,
            target_label=target_label,
            claimed_model=claimed_model,
            prompt_count_total=prompt_count_total,
            prompt_count_completed=prompt_count_completed,
            prompt_count_scoreable=prompt_count_scoreable,
            answer_coverage_ratio=_ratio(answer_visible_count, prompt_count_total),
            reasoning_coverage_ratio=_ratio(reasoning_visible_count, prompt_count_total),
            prompts=prompt_results,
        )


def _ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
