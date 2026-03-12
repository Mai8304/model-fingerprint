from __future__ import annotations

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import RuntimePolicySnapshot
from modelfingerprint.services.runtime_policy import (
    HIGH_BUDGET_OUTPUT_TOKEN_CAP,
    resolve_prompt_runtime_intent,
    resolve_runtime_policy,
)


def build_endpoint(
    *,
    supports_output_token_cap: bool = True,
    runtime_profile_id: str | None = None,
    read_seconds: int = 120,
) -> EndpointProfile:
    return EndpointProfile.model_validate(
        {
            "id": "test-openai-compatible",
            "dialect": "openai_chat_v1",
            "protocol_family": "openai_compatible",
            "base_url": "https://api.example.com/v1",
            "model": "gpt-4o-mini",
            "auth": {
                "kind": "bearer_env",
                "env_var": "MODEL_FINGERPRINT_API_KEY",
            },
            "runtime_profile_id": runtime_profile_id,
            "capabilities": {
                "exposes_reasoning_text": True,
                "supports_json_object_response": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_output_token_cap": supports_output_token_cap,
            },
            "request_mapping": {
                "output_token_cap_field": "max_tokens",
                "json_response_shape": {"type": "json_object"},
            },
            "response_mapping": {
                "answer_text_path": "choices.0.message.content",
                "reasoning_text_path": "choices.0.message.reasoning_content",
                "finish_reason_path": "choices.0.finish_reason",
                "usage_paths": {
                    "prompt_tokens": "usage.prompt_tokens",
                    "output_tokens": "usage.completion_tokens",
                    "total_tokens": "usage.total_tokens",
                    "reasoning_tokens": "usage.completion_tokens_details.reasoning_tokens",
                },
            },
            "timeout_policy": {
                "connect_seconds": 10,
                "read_seconds": read_seconds,
            },
            "retry_policy": {
                "max_attempts": 2,
                "retryable_statuses": [408, 429, 500, 502, 503, 504],
            },
        }
    )


def build_prompt(
    *,
    response_format: str = "json_object",
    reasoning_mode: str = "capture_if_available",
    canonicalizer: str = "tolerant_json_v3",
    required_capabilities: list[str] | None = None,
) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p021",
            "name": "grounded_identity_resolution",
            "family": "evidence_grounding",
            "intent": "detect grounded JSON execution",
            "messages": [
                {
                    "role": "system",
                    "content": "Return only the requested JSON object.",
                },
                {
                    "role": "user",
                    "content": "Reply with the requested JSON object.",
                },
            ],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 96,
                "response_format": response_format,
                "reasoning_mode": reasoning_mode,
            },
            "output_contract": {
                "id": canonicalizer,
                "canonicalizer": canonicalizer,
            },
            "extractors": {
                "answer": "evidence_grounding_v3",
                "reasoning": "reasoning_trace_v1",
                "transport": "completion_metadata_v1",
            },
            "required_capabilities": required_capabilities or ["chat_completions"],
            "weight_hint": 0.9,
            "tags": ["grounding", "json"],
            "risk_level": "low",
        }
    )


def test_resolve_runtime_policy_builds_intent_tiers_for_standard_profile() -> None:
    resolved = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "supported",
                }
            }
        },
        endpoint=build_endpoint(),
    )

    assert resolved.policy_id == "intent_tiered_runtime_v1"
    assert resolved.thinking_probe_status == "supported"
    assert resolved.execution_class == "thinking"
    assert resolved.default_intent == "structured_extraction"
    assert [policy.intent for policy in resolved.intent_policies] == [
        "structured_extraction",
        "capability_probe",
        "long_reasoning",
    ]

    structured = resolved.intent_policies[0]
    assert len(structured.attempts) == 3
    assert structured.attempts[0].use_prompt_output_token_cap is True
    assert structured.attempts[0].first_byte_timeout_seconds == 30
    assert structured.attempts[0].idle_timeout_seconds == 15
    assert structured.attempts[0].total_deadline_seconds == 90
    assert structured.attempts[0].escalate_on == [
        "finish_reason_length",
        "missing_answer_text",
        "invalid_structured_output",
        "retryable_transport_error",
    ]
    assert structured.attempts[1].output_token_cap_multiplier == 2.0
    assert structured.attempts[2].output_token_cap == HIGH_BUDGET_OUTPUT_TOKEN_CAP

    capability_probe = resolved.intent_policies[1]
    assert len(capability_probe.attempts) == 1
    assert capability_probe.attempts[0].output_token_cap == 256
    assert capability_probe.attempts[0].first_byte_timeout_seconds == 15
    assert capability_probe.attempts[0].total_deadline_seconds == 30

    long_reasoning = resolved.intent_policies[2]
    assert len(long_reasoning.attempts) == 2
    assert long_reasoning.attempts[0].output_token_cap == 1500
    assert long_reasoning.attempts[1].output_token_cap == HIGH_BUDGET_OUTPUT_TOKEN_CAP
    assert long_reasoning.attempts[0].total_deadline_seconds == 120
    assert long_reasoning.attempts[1].total_deadline_seconds == 120


def test_resolve_runtime_policy_clamps_attempt_deadlines_and_output_caps() -> None:
    resolved = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "accepted_but_ignored",
                }
            }
        },
        endpoint=build_endpoint(
            supports_output_token_cap=False,
            runtime_profile_id="reasoning_openai_compatible_v1",
            read_seconds=100,
        ),
    )

    assert resolved.execution_class == "non_thinking"
    structured = resolved.intent_policies[0]
    assert [attempt.total_deadline_seconds for attempt in structured.attempts] == [100, 100, 100]
    assert all(attempt.output_token_cap is None for attempt in structured.attempts)
    assert all(attempt.output_token_cap_multiplier is None for attempt in structured.attempts)
    assert structured.attempts[0].first_byte_timeout_seconds == 40
    assert structured.attempts[0].idle_timeout_seconds == 20

    long_reasoning = resolved.intent_policies[2]
    assert [attempt.total_deadline_seconds for attempt in long_reasoning.attempts] == [100, 100]
    assert all(attempt.output_token_cap is None for attempt in long_reasoning.attempts)


def test_resolve_runtime_policy_applies_structured_thinking_disable_runtime_profile() -> None:
    resolved = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "supported",
                }
            }
        },
        endpoint=build_endpoint(runtime_profile_id="structured_extraction_disable_thinking_v1"),
    )

    structured = resolved.intent_policies[0]
    assert structured.attempts[0].request_body_overrides == {"thinking": {"type": "disabled"}}
    assert structured.attempts[1].request_body_overrides == {"thinking": {"type": "disabled"}}
    assert structured.attempts[2].request_body_overrides == {}


def test_resolve_runtime_policy_uses_reasoning_visible_structured_runtime_profile() -> None:
    resolved = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "supported",
                }
            }
        },
        endpoint=build_endpoint(
            runtime_profile_id="reasoning_visible_structured_v1",
            read_seconds=200,
        ),
    )

    structured = resolved.intent_policies[0]
    assert [attempt.output_token_cap for attempt in structured.attempts] == [1500, 3000]
    assert [attempt.total_deadline_seconds for attempt in structured.attempts] == [120, 180]
    assert all(attempt.use_prompt_output_token_cap is False for attempt in structured.attempts)
    assert all(attempt.output_token_cap_multiplier is None for attempt in structured.attempts)


def test_resolve_prompt_runtime_intent_prefers_prompt_contract_over_thinking_probe() -> None:
    structured_prompt = build_prompt()
    long_reasoning_prompt = build_prompt(
        response_format="text",
        reasoning_mode="require_visible",
        canonicalizer="tolerant_json_v3",
        required_capabilities=["chat_completions", "visible_reasoning"],
    )

    assert resolve_prompt_runtime_intent(structured_prompt) == "structured_extraction"
    assert resolve_prompt_runtime_intent(long_reasoning_prompt) == "long_reasoning"


def test_runtime_policy_snapshot_backfills_intent_policies_from_legacy_payload() -> None:
    payload = RuntimePolicySnapshot.model_validate(
        {
            "policy_id": "single_request_progress_runtime_v1",
            "thinking_probe_status": "supported",
            "execution_class": "thinking",
            "no_data_checkpoints_seconds": [60, 90],
            "progress_poll_interval_seconds": 10,
            "total_deadline_seconds": 120,
            "output_token_cap": 3000,
        }
    )

    assert payload.default_intent == "long_reasoning"
    assert [policy.intent for policy in payload.intent_policies] == ["long_reasoning"]
    assert payload.intent_policies[0].attempts[0].first_byte_timeout_seconds == 90
    assert payload.intent_policies[0].attempts[0].idle_timeout_seconds == 10
    assert payload.intent_policies[0].attempts[0].total_deadline_seconds == 120
    assert payload.intent_policies[0].attempts[0].output_token_cap == 3000
