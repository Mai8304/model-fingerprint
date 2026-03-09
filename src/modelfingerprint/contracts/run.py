from __future__ import annotations

from pydantic import Field

from modelfingerprint.contracts._common import (
    ContractModel,
    FeaturePrimitive,
    PromptId,
    SuiteId,
)


class UsageMetadata(ContractModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class PromptRunResult(ContractModel):
    prompt_id: PromptId
    raw_output: str
    usage: UsageMetadata
    features: dict[str, FeaturePrimitive] = Field(min_length=1)


class RunArtifact(ContractModel):
    run_id: str = Field(min_length=1)
    suite_id: SuiteId
    target_label: str = Field(min_length=1)
    claimed_model: str | None = None
    prompts: list[PromptRunResult] = Field(min_length=1)
