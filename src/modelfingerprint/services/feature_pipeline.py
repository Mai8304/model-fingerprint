from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from modelfingerprint.canonicalizers.base import CanonicalizationError
from modelfingerprint.canonicalizers.registry import (
    CanonicalizerRegistry,
)
from modelfingerprint.canonicalizers.registry import (
    build_default_registry as build_default_canonicalizer_registry,
)
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
from modelfingerprint.extractors.registry import SURFACE_EXTRACTOR_NAME, ExtractorRegistry

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
    def __init__(
        self,
        registry: ExtractorRegistry,
        canonicalizers: CanonicalizerRegistry | None = None,
    ) -> None:
        self._registry = registry
        self._canonicalizers = canonicalizers or build_default_canonicalizer_registry()

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
            status = execution.status
            canonical_output = execution.canonical_output
            canonicalization_events = list(execution.canonicalization_events)
            error = execution.error
            usage = execution.usage or (
                execution.completion.usage if execution.completion is not None else None
            )

            if status == "completed":
                prompt_count_completed += 1
                if execution.raw_output is not None:
                    answer_visible_count += 1
                    if canonical_output is None:
                        try:
                            canonical_output, new_events = self._canonicalizers.canonicalize(
                                execution.prompt,
                                execution.raw_output,
                            )
                            canonicalization_events.extend(new_events)
                        except CanonicalizationError as exc:
                            status = "canonicalization_error"
                            error = PromptExecutionError(
                                kind=exc.code,
                                message=exc.message,
                                retryable=False,
                            )
                if (
                    status == "completed"
                    and execution.raw_output is not None
                    and canonical_output is not None
                ):
                    if (
                        execution.prompt.extractors.score is not None
                        and self._registry.has(execution.prompt.extractors.score)
                    ):
                        features.update(
                            _namespace(
                                "score",
                                self._registry.extract_score(execution.prompt, canonical_output),
                            )
                        )
                    features.update(
                        _namespace(
                            "answer",
                            self._registry.extract_answer(execution.prompt, canonical_output),
                        )
                    )
                    if (
                        execution.completion is not None
                        and execution.completion.reasoning_visible
                        and execution.completion.reasoning_text
                        and execution.prompt.extractors.reasoning is not None
                        and self._registry.has(execution.prompt.extractors.reasoning)
                    ):
                        features.update(
                            _namespace(
                                "reasoning",
                                self._registry.extract_reasoning(
                                    execution.prompt,
                                    execution.completion.reasoning_text,
                                ),
                            )
                        )
                    if (
                        execution.completion is not None
                        and execution.prompt.extractors.transport is not None
                        and self._registry.has(execution.prompt.extractors.transport)
                    ):
                        features.update(
                            _namespace(
                                "transport",
                                self._registry.extract_transport(
                                    execution.prompt,
                                    execution.completion,
                                ),
                            )
                        )
                    if self._registry.has(SURFACE_EXTRACTOR_NAME):
                        features.update(
                            _namespace(
                                "surface",
                                self._registry.extract_surface(
                                    raw_output=execution.raw_output,
                                    canonical_output=canonical_output,
                                    canonicalization_events=canonicalization_events,
                                ),
                            )
                        )
                    if features:
                        prompt_count_scoreable += 1
                if execution.completion is not None and execution.completion.reasoning_visible:
                    reasoning_visible_count += 1

            prompt_results.append(
                PromptRunResult(
                    status=status,
                    prompt_id=execution.prompt.id,
                    raw_output=execution.raw_output,
                    usage=usage,
                    request_snapshot=execution.request_snapshot,
                    completion=execution.completion,
                    canonical_output=canonical_output,
                    canonicalization_events=canonicalization_events,
                    features=features,
                    error=error,
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


def _namespace(prefix: str, feature_map: FeatureMap) -> FeatureMap:
    return {f"{prefix}.{name}": value for name, value in feature_map.items()}
