from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from modelfingerprint.contracts._common import (
    ContractModel,
    FeaturePrimitive,
    PromptId,
    SuiteId,
)
from modelfingerprint.contracts.prompt import GenerationSpec, PromptMessage


class UsageMetadata(ContractModel):
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    reasoning_tokens: int = Field(ge=0, default=0)
    total_tokens: int = Field(ge=0)


class PromptRequestSnapshot(ContractModel):
    messages: list[PromptMessage] = Field(min_length=1)
    generation: GenerationSpec


class NormalizedCompletion(ContractModel):
    answer_text: str = Field(min_length=1)
    reasoning_text: str | None = None
    reasoning_visible: bool = False
    finish_reason: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    raw_response_path: str | None = None
    usage: UsageMetadata


class CanonicalizedOutput(ContractModel):
    format_id: str = Field(min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)


class CanonicalizationEvent(ContractModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)


class PromptExecutionError(ContractModel):
    kind: str = Field(min_length=1)
    message: str = Field(min_length=1)
    retryable: bool = False
    http_status: int | None = Field(default=None, ge=100, le=599)


class ProtocolCompatibility(ContractModel):
    satisfied: bool
    required_capabilities: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)


class PromptRunResult(ContractModel):
    status: Literal[
        "completed",
        "timeout",
        "transport_error",
        "unsupported_capability",
        "truncated",
        "invalid_response",
        "canonicalization_error",
    ] = "completed"
    prompt_id: PromptId
    raw_output: str | None = None
    usage: UsageMetadata | None = None
    request_snapshot: PromptRequestSnapshot | None = None
    completion: NormalizedCompletion | None = None
    canonical_output: CanonicalizedOutput | None = None
    canonicalization_events: list[CanonicalizationEvent] = Field(default_factory=list)
    features: dict[str, FeaturePrimitive] = Field(default_factory=dict)
    error: PromptExecutionError | None = None

    @model_validator(mode="after")
    def validate_completed_prompt(self) -> PromptRunResult:
        if self.status == "completed":
            if self.usage is None:
                raise ValueError("completed prompts must include usage")
            if not self.features:
                raise ValueError("completed prompts must include extracted features")
        return self


class RunArtifact(ContractModel):
    run_id: str = Field(min_length=1)
    suite_id: SuiteId
    target_label: str = Field(min_length=1)
    claimed_model: str | None = None
    endpoint_profile_id: str | None = None
    prompt_count_total: int | None = Field(default=None, ge=0)
    prompt_count_completed: int | None = Field(default=None, ge=0)
    prompt_count_scoreable: int | None = Field(default=None, ge=0)
    answer_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    protocol_compatibility: ProtocolCompatibility | None = None
    trace_dir: str | None = None
    prompts: list[PromptRunResult] = Field(min_length=1)
