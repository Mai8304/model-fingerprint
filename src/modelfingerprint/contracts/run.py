from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from modelfingerprint.contracts._common import (
    ContractModel,
    FeaturePrimitive,
    Probability,
    ProbeCapabilityId,
    ProbeCapabilityStatus,
    PromptId,
    RuntimeExecutionClass,
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
    answer_text: str = ""
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


class CapabilityProbeOutcome(ContractModel):
    status: ProbeCapabilityStatus
    detail: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    latency_ms: int | None = Field(default=None, ge=0)
    evidence: dict[str, FeaturePrimitive] = Field(default_factory=dict)


class CapabilityProbeResult(ContractModel):
    probe_mode: str = Field(min_length=1)
    probe_version: str = Field(min_length=1)
    coverage_ratio: Probability
    capabilities: dict[ProbeCapabilityId, CapabilityProbeOutcome] = Field(min_length=1)


RuntimeRequestIntent = Literal[
    "structured_extraction",
    "capability_probe",
    "long_reasoning",
]
RuntimeEscalationSignal = Literal[
    "finish_reason_length",
    "missing_answer_text",
    "invalid_structured_output",
    "missing_reasoning_text",
    "retryable_transport_error",
]


class RuntimeAttemptPolicy(ContractModel):
    attempt_index: int = Field(ge=1)
    use_prompt_output_token_cap: bool = False
    output_token_cap: int | None = Field(default=None, ge=1)
    output_token_cap_multiplier: float | None = Field(default=None, gt=0.0)
    request_body_overrides: dict[str, object] = Field(default_factory=dict)
    connect_timeout_seconds: int = Field(gt=0)
    write_timeout_seconds: int = Field(gt=0)
    first_byte_timeout_seconds: int = Field(gt=0)
    idle_timeout_seconds: int = Field(gt=0)
    total_deadline_seconds: int = Field(gt=0)
    escalate_on: list[RuntimeEscalationSignal] = Field(default_factory=list)


class RuntimeIntentPolicy(ContractModel):
    intent: RuntimeRequestIntent
    attempts: list[RuntimeAttemptPolicy] = Field(min_length=1)


class RuntimePolicySnapshot(ContractModel):
    policy_id: str = Field(min_length=1)
    thinking_probe_status: ProbeCapabilityStatus
    execution_class: RuntimeExecutionClass
    default_intent: RuntimeRequestIntent | None = None
    intent_policies: list[RuntimeIntentPolicy] = Field(default_factory=list)
    no_data_checkpoints_seconds: list[int] | None = Field(default=None, min_length=1)
    progress_poll_interval_seconds: int | None = Field(default=None, gt=0)
    total_deadline_seconds: int | None = Field(default=None, gt=0)
    output_token_cap: int | None = Field(default=None, ge=1)
    round_windows_seconds: list[int] | None = Field(default=None, min_length=1)
    max_rounds: int | None = Field(default=None, ge=1)

    @model_validator(mode="before")
    @classmethod
    def upgrade_legacy_runtime_policy(
        cls,
        value: object,
    ) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if data.get("intent_policies"):
            return data
        total_deadline = int(data.get("total_deadline_seconds") or 120)
        no_data_checkpoints = list(data.get("no_data_checkpoints_seconds") or [60])
        progress_poll_interval = int(data.get("progress_poll_interval_seconds") or 10)
        default_intent = data.get("default_intent")
        if default_intent not in {
            "structured_extraction",
            "capability_probe",
            "long_reasoning",
        }:
            default_intent = (
                "long_reasoning"
                if data.get("execution_class") == "thinking"
                else "structured_extraction"
            )
        data["default_intent"] = default_intent
        data["intent_policies"] = [
            {
                "intent": default_intent,
                "attempts": [
                    {
                        "attempt_index": 1,
                        "output_token_cap": data.get("output_token_cap"),
                        "connect_timeout_seconds": 10,
                        "write_timeout_seconds": 10,
                        "first_byte_timeout_seconds": int(no_data_checkpoints[-1]),
                        "idle_timeout_seconds": progress_poll_interval,
                        "total_deadline_seconds": total_deadline,
                        "escalate_on": [],
                    }
                ],
            }
        ]
        return data

    @model_validator(mode="after")
    def validate_runtime_policy(self) -> RuntimePolicySnapshot:
        if not self.intent_policies:
            raise ValueError("runtime policy must include at least one intent policy")
        intents = {policy.intent for policy in self.intent_policies}
        if self.default_intent is None:
            self.default_intent = self.intent_policies[0].intent
        if self.default_intent not in intents:
            raise ValueError("runtime policy default_intent must exist in intent_policies")
        return self

    def policy_for_intent(self, intent: RuntimeRequestIntent) -> RuntimeIntentPolicy:
        for policy in self.intent_policies:
            if policy.intent == intent:
                return policy
        assert self.default_intent is not None
        for policy in self.intent_policies:
            if policy.intent == self.default_intent:
                return policy
        raise ValueError(f"missing runtime intent policy: {intent}")


class PromptAttemptSummary(ContractModel):
    request_attempt_index: int | None = Field(default=None, ge=1)
    read_timeout_seconds: int = Field(gt=0)
    runtime_intent: RuntimeRequestIntent | None = None
    runtime_tier_index: int | None = Field(default=None, ge=0)
    output_token_cap: int | None = Field(default=None, ge=1)
    connect_timeout_seconds: int | None = Field(default=None, gt=0)
    write_timeout_seconds: int | None = Field(default=None, gt=0)
    first_byte_timeout_seconds: int | None = Field(default=None, gt=0)
    idle_timeout_seconds: int | None = Field(default=None, gt=0)
    total_deadline_seconds: int | None = Field(default=None, gt=0)
    status: Literal[
        "completed",
        "timeout",
        "transport_error",
        "unsupported_capability",
        "truncated",
        "invalid_response",
        "canonicalization_error",
    ]
    error_kind: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    latency_ms: int | None = Field(default=None, ge=0)
    finish_reason: str | None = None
    answer_text_present: bool
    reasoning_visible: bool | None = None
    bytes_received: int | None = Field(default=None, ge=0)
    first_byte_latency_ms: int | None = Field(default=None, ge=0)
    last_progress_latency_ms: int | None = Field(default=None, ge=0)
    completed: bool | None = None
    abort_reason: str | None = None
    round_index: int | None = Field(default=None, ge=1)
    window_index: int | None = Field(default=None, ge=1)
    http_attempt_index: int | None = Field(default=None, ge=1)


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
    attempts: list[PromptAttemptSummary] = Field(default_factory=list)
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
    runtime_policy: RuntimePolicySnapshot | None = None
    capability_probe: CapabilityProbeResult | None = None
    protocol_compatibility: ProtocolCompatibility | None = None
    trace_dir: str | None = None
    prompts: list[PromptRunResult] = Field(min_length=1)
