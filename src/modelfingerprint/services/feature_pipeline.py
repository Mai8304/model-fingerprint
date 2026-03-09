from __future__ import annotations

from dataclasses import dataclass

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import PromptRunResult, RunArtifact, UsageMetadata
from modelfingerprint.extractors.registry import ExtractorRegistry


@dataclass(frozen=True)
class PromptExecutionResult:
    prompt: PromptDefinition
    raw_output: str
    usage: UsageMetadata


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
        prompt_results = [
            PromptRunResult(
                prompt_id=execution.prompt.id,
                raw_output=execution.raw_output,
                usage=execution.usage,
                features=self._registry.extract(execution.prompt, execution.raw_output),
            )
            for execution in executions
        ]

        return RunArtifact(
            run_id=run_id,
            suite_id=suite_id,
            target_label=target_label,
            claimed_model=claimed_model,
            prompts=prompt_results,
        )
