from __future__ import annotations

from datetime import date
from pathlib import Path

from modelfingerprint.adapters.openai_chat import ChatCompletionTransport
from modelfingerprint.contracts.run import UsageMetadata
from modelfingerprint.extractors.registry import ExtractorRegistry, build_default_registry
from modelfingerprint.services.feature_pipeline import FeaturePipeline, PromptExecutionResult
from modelfingerprint.services.prompt_bank import (
    load_candidate_prompts,
    load_suites,
    validate_suite_references,
    validate_suite_subset,
)
from modelfingerprint.services.run_writer import RunWriter
from modelfingerprint.settings import RepositoryPaths


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
        validate_suite_subset(suites["default-v1"], suites["screening-v1"])
        suite = suites[suite_id]
        executions: list[PromptExecutionResult] = []

        for prompt_id in suite.prompt_ids:
            prompt = prompts[prompt_id]
            result = self._transport.complete(prompt)
            executions.append(
                PromptExecutionResult(
                    prompt=prompt,
                    raw_output=result.content,
                    usage=UsageMetadata(
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        total_tokens=result.total_tokens,
                    ),
                )
            )

        artifact = FeaturePipeline(self._registry).build_run_artifact(
            run_id=f"{target_label}.{suite_id}",
            suite_id=suite.id,
            target_label=target_label,
            claimed_model=claimed_model,
            executions=executions,
        )

        return RunWriter(self._paths).write(artifact, run_date or date.today())
