from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol, cast

from modelfingerprint.adapters.openai_chat import ChatCompletionTransport
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import UsageMetadata
from modelfingerprint.extractors.registry import ExtractorRegistry, build_default_registry
from modelfingerprint.services.feature_pipeline import FeaturePipeline, PromptExecutionResult
from modelfingerprint.services.prompt_bank import (
    FINGERPRINT_SUITE_ID,
    QUICK_CHECK_SUITE_ID,
    load_candidate_prompts,
    load_suites,
    validate_suite_references,
    validate_suite_subset,
)
from modelfingerprint.services.run_writer import RunWriter
from modelfingerprint.settings import RepositoryPaths


class PromptExecutionTransport(Protocol):
    def execute(self, prompt: PromptDefinition) -> PromptExecutionResult: ...


class SuiteRunner:
    def __init__(
        self,
        paths: RepositoryPaths,
        transport: ChatCompletionTransport,
        registry: ExtractorRegistry | None = None,
    ) -> None:
        self._paths = paths
        self._transport = transport
        self._registry = registry or build_default_registry(paths.root / "extractors")

    def run_suite(
        self,
        suite_id: str,
        target_label: str,
        claimed_model: str | None = None,
        run_date: date | None = None,
    ) -> Path:
        prompts = load_candidate_prompts(self._paths.prompt_bank_dir / "candidates")
        suites = load_suites(self._paths.prompt_bank_dir / "suites")
        validate_suite_references(prompts, suites)
        validate_suite_subset(suites[FINGERPRINT_SUITE_ID], suites[QUICK_CHECK_SUITE_ID])
        suite = suites[suite_id]
        executions: list[PromptExecutionResult] = []

        for prompt_id in suite.prompt_ids:
            prompt = prompts[prompt_id]
            executions.append(self._execute_prompt(prompt))

        artifact = FeaturePipeline(self._registry).build_run_artifact(
            run_id=f"{target_label}.{suite_id}",
            suite_id=suite.id,
            target_label=target_label,
            claimed_model=claimed_model,
            executions=executions,
        )

        return RunWriter(self._paths).write(artifact, run_date or date.today())

    def _execute_prompt(self, prompt: PromptDefinition) -> PromptExecutionResult:
        if hasattr(self._transport, "execute"):
            executor = cast(PromptExecutionTransport, self._transport)
            return executor.execute(prompt)

        result = self._transport.complete(prompt)
        return PromptExecutionResult(
            prompt=prompt,
            raw_output=result.content,
            usage=UsageMetadata(
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                total_tokens=result.total_tokens,
            ),
        )
