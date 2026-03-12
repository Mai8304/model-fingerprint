from __future__ import annotations

import math
from collections.abc import Mapping
from typing import cast

from modelfingerprint.contracts._common import ProbeCapabilityStatus, RuntimeExecutionClass
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import (
    CapabilityProbeResult,
    RuntimeAttemptPolicy,
    RuntimeIntentPolicy,
    RuntimePolicySnapshot,
    RuntimeRequestIntent,
)

RUNTIME_POLICY_ID = "intent_tiered_runtime_v1"
DEFAULT_RUNTIME_PROFILE_ID = "standard_openai_compatible_v1"
STRUCTURED_EXTRACTION_DISABLE_THINKING_PROFILE_ID = "structured_extraction_disable_thinking_v1"
REASONING_VISIBLE_STRUCTURED_PROFILE_ID = "reasoning_visible_structured_v1"
HIGH_BUDGET_OUTPUT_TOKEN_CAP = 3000
LONG_REASONING_OUTPUT_TOKEN_CAP = 1500
CAPABILITY_PROBE_OUTPUT_TOKEN_CAP = 256


def resolve_runtime_policy(
    *,
    capability_probe_payload: CapabilityProbeResult | Mapping[str, object] | None,
    endpoint: EndpointProfile,
) -> RuntimePolicySnapshot:
    thinking_status = _thinking_probe_status(capability_probe_payload)
    execution_class: RuntimeExecutionClass = (
        "thinking" if thinking_status == "supported" else "non_thinking"
    )
    runtime_profile_id = endpoint.runtime_profile_id or DEFAULT_RUNTIME_PROFILE_ID
    intent_policies = _build_intent_policies(
        endpoint=endpoint,
        runtime_profile_id=runtime_profile_id,
    )
    return RuntimePolicySnapshot(
        policy_id=RUNTIME_POLICY_ID,
        thinking_probe_status=thinking_status,
        execution_class=execution_class,
        default_intent="structured_extraction",
        intent_policies=intent_policies,
    )


def resolve_prompt_runtime_intent(prompt: PromptDefinition) -> RuntimeRequestIntent:
    if (
        prompt.generation.reasoning_mode == "require_visible"
        or "visible_reasoning" in prompt.required_capabilities
    ):
        return "long_reasoning"
    if (
        prompt.generation.response_format == "json_object"
        or prompt.output_contract.canonicalizer == "tolerant_json_v3"
    ):
        return "structured_extraction"
    return "structured_extraction"


def resolve_runtime_attempts(
    *,
    runtime_policy: RuntimePolicySnapshot,
    prompt: PromptDefinition,
) -> tuple[RuntimeRequestIntent, list[RuntimeAttemptPolicy]]:
    intent = resolve_prompt_runtime_intent(prompt)
    policy = runtime_policy.policy_for_intent(intent)
    return intent, list(policy.attempts)


def resolve_output_token_cap(
    *,
    prompt: PromptDefinition,
    endpoint: EndpointProfile,
    attempt: RuntimeAttemptPolicy,
) -> int | None:
    if not endpoint.capabilities.supports_output_token_cap:
        return None
    if attempt.use_prompt_output_token_cap:
        return prompt.generation.max_output_tokens
    if attempt.output_token_cap is not None:
        return attempt.output_token_cap
    if attempt.output_token_cap_multiplier is not None:
        return int(math.ceil(prompt.generation.max_output_tokens * attempt.output_token_cap_multiplier))
    return None


def _build_intent_policies(
    *,
    endpoint: EndpointProfile,
    runtime_profile_id: str,
) -> list[RuntimeIntentPolicy]:
    structured_attempts = _build_structured_extraction_attempts(
        endpoint=endpoint,
        runtime_profile_id=runtime_profile_id,
    )

    return [
        RuntimeIntentPolicy(
            intent="structured_extraction",
            attempts=structured_attempts,
        ),
        RuntimeIntentPolicy(
            intent="capability_probe",
            attempts=[
                _build_attempt(
                    endpoint=endpoint,
                    attempt_index=1,
                    output_token_cap=CAPABILITY_PROBE_OUTPUT_TOKEN_CAP,
                    first_byte_timeout_seconds=15,
                    idle_timeout_seconds=10,
                    total_deadline_seconds=30,
                    escalate_on=[],
                )
            ],
        ),
        RuntimeIntentPolicy(
            intent="long_reasoning",
            attempts=[
                _build_attempt(
                    endpoint=endpoint,
                    attempt_index=1,
                    output_token_cap=LONG_REASONING_OUTPUT_TOKEN_CAP,
                    first_byte_timeout_seconds=45,
                    idle_timeout_seconds=20,
                    total_deadline_seconds=120,
                    escalate_on=[
                        "finish_reason_length",
                        "missing_answer_text",
                        "missing_reasoning_text",
                        "retryable_transport_error",
                    ],
                ),
                _build_attempt(
                    endpoint=endpoint,
                    attempt_index=2,
                    output_token_cap=HIGH_BUDGET_OUTPUT_TOKEN_CAP,
                    first_byte_timeout_seconds=60,
                    idle_timeout_seconds=30,
                    total_deadline_seconds=180,
                    escalate_on=[],
                ),
            ],
        ),
    ]


def _build_structured_extraction_attempts(
    *,
    endpoint: EndpointProfile,
    runtime_profile_id: str,
) -> list[RuntimeAttemptPolicy]:
    if runtime_profile_id == REASONING_VISIBLE_STRUCTURED_PROFILE_ID:
        return [
            _build_attempt(
                endpoint=endpoint,
                attempt_index=1,
                output_token_cap=LONG_REASONING_OUTPUT_TOKEN_CAP,
                first_byte_timeout_seconds=45,
                idle_timeout_seconds=20,
                total_deadline_seconds=120,
                escalate_on=[
                    "finish_reason_length",
                    "missing_answer_text",
                    "invalid_structured_output",
                    "retryable_transport_error",
                ],
            ),
            _build_attempt(
                endpoint=endpoint,
                attempt_index=2,
                output_token_cap=HIGH_BUDGET_OUTPUT_TOKEN_CAP,
                first_byte_timeout_seconds=60,
                idle_timeout_seconds=30,
                total_deadline_seconds=180,
                escalate_on=[],
            ),
        ]

    if runtime_profile_id == "reasoning_openai_compatible_v1":
        structured_deadlines = [(40, 20, 120), (50, 25, 150), (60, 30, 180)]
    else:
        structured_deadlines = [(30, 15, 90), (40, 20, 120), (60, 30, 180)]

    return [
        _build_attempt(
            endpoint=endpoint,
            attempt_index=1,
            use_prompt_output_token_cap=True,
            request_body_overrides=_structured_request_overrides(
                runtime_profile_id=runtime_profile_id,
                attempt_index=1,
            ),
            first_byte_timeout_seconds=structured_deadlines[0][0],
            idle_timeout_seconds=structured_deadlines[0][1],
            total_deadline_seconds=structured_deadlines[0][2],
            escalate_on=[
                "finish_reason_length",
                "missing_answer_text",
                "invalid_structured_output",
                "retryable_transport_error",
            ],
        ),
        _build_attempt(
            endpoint=endpoint,
            attempt_index=2,
            output_token_cap_multiplier=2.0,
            request_body_overrides=_structured_request_overrides(
                runtime_profile_id=runtime_profile_id,
                attempt_index=2,
            ),
            first_byte_timeout_seconds=structured_deadlines[1][0],
            idle_timeout_seconds=structured_deadlines[1][1],
            total_deadline_seconds=structured_deadlines[1][2],
            escalate_on=[
                "finish_reason_length",
                "missing_answer_text",
                "invalid_structured_output",
                "retryable_transport_error",
            ],
        ),
        _build_attempt(
            endpoint=endpoint,
            attempt_index=3,
            output_token_cap=HIGH_BUDGET_OUTPUT_TOKEN_CAP,
            first_byte_timeout_seconds=structured_deadlines[2][0],
            idle_timeout_seconds=structured_deadlines[2][1],
            total_deadline_seconds=structured_deadlines[2][2],
            escalate_on=[],
        ),
    ]


def _build_attempt(
    *,
    endpoint: EndpointProfile,
    attempt_index: int,
    first_byte_timeout_seconds: int,
    idle_timeout_seconds: int,
    total_deadline_seconds: int,
    use_prompt_output_token_cap: bool = False,
    output_token_cap: int | None = None,
    output_token_cap_multiplier: float | None = None,
    request_body_overrides: Mapping[str, object] | None = None,
    escalate_on: list[str],
) -> RuntimeAttemptPolicy:
    clamped_total = min(total_deadline_seconds, endpoint.timeout_policy.read_seconds)
    if endpoint.capabilities.supports_output_token_cap:
        resolved_output_token_cap = output_token_cap
        resolved_output_token_cap_multiplier = output_token_cap_multiplier
        resolved_use_prompt_output_token_cap = use_prompt_output_token_cap
    else:
        resolved_output_token_cap = None
        resolved_output_token_cap_multiplier = None
        resolved_use_prompt_output_token_cap = False
    return RuntimeAttemptPolicy(
        attempt_index=attempt_index,
        use_prompt_output_token_cap=resolved_use_prompt_output_token_cap,
        output_token_cap=resolved_output_token_cap,
        output_token_cap_multiplier=resolved_output_token_cap_multiplier,
        request_body_overrides={} if request_body_overrides is None else dict(request_body_overrides),
        connect_timeout_seconds=endpoint.timeout_policy.connect_seconds,
        write_timeout_seconds=endpoint.timeout_policy.connect_seconds,
        first_byte_timeout_seconds=min(first_byte_timeout_seconds, clamped_total),
        idle_timeout_seconds=min(idle_timeout_seconds, clamped_total),
        total_deadline_seconds=clamped_total,
        escalate_on=cast(list, list(escalate_on)),
    )


def _structured_request_overrides(
    *,
    runtime_profile_id: str,
    attempt_index: int,
) -> dict[str, object]:
    if runtime_profile_id != STRUCTURED_EXTRACTION_DISABLE_THINKING_PROFILE_ID:
        return {}
    if attempt_index not in {1, 2}:
        return {}
    return {"thinking": {"type": "disabled"}}


def _thinking_probe_status(
    capability_probe_payload: CapabilityProbeResult | Mapping[str, object] | None,
) -> ProbeCapabilityStatus:
    if capability_probe_payload is None:
        return "insufficient_evidence"
    if isinstance(capability_probe_payload, CapabilityProbeResult):
        outcome = capability_probe_payload.capabilities.get("thinking")
        return outcome.status if outcome is not None else "insufficient_evidence"
    results = capability_probe_payload.get("results")
    if not isinstance(results, Mapping):
        return "insufficient_evidence"
    thinking = results.get("thinking")
    if not isinstance(thinking, Mapping):
        return "insufficient_evidence"
    status = thinking.get("status")
    if status in {
        "supported",
        "accepted_but_ignored",
        "unsupported",
        "insufficient_evidence",
    }:
        return cast(ProbeCapabilityStatus, status)
    return "insufficient_evidence"
