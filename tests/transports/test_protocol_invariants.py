from __future__ import annotations

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.services.runtime_policy import resolve_runtime_policy
from modelfingerprint.transports.http_client import HttpProgressSnapshot, HttpTerminalResult
from modelfingerprint.transports.live_runner import LiveRunner


def build_prompt() -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p021",
            "name": "grounded_identity_resolution",
            "family": "evidence_grounding",
            "intent": "verify protocol invariants for grounded JSON prompts",
            "messages": [
                {
                    "role": "system",
                    "content": "Return only the requested JSON object.",
                },
                {
                    "role": "user",
                    "content": (
                        "Reply with a JSON object containing task_result, evidence, unknowns, and violations."
                    ),
                },
            ],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 96,
                "response_format": "json_object",
                "reasoning_mode": "capture_if_available",
            },
            "output_contract": {"id": "tolerant_json_v3", "canonicalizer": "tolerant_json_v3"},
            "extractors": {
                "answer": "evidence_grounding_v3",
                "reasoning": "reasoning_trace_v1",
                "transport": "completion_metadata_v1",
            },
            "required_capabilities": ["chat_completions", "json_object_response"],
            "weight_hint": 0.9,
            "tags": ["grounding", "json"],
            "risk_level": "low",
        }
    )


def build_endpoint(
    *,
    supports_json_object_response: bool,
    output_token_cap_field: str,
) -> EndpointProfile:
    request_mapping: dict[str, object] = {
        "output_token_cap_field": output_token_cap_field,
    }
    if supports_json_object_response:
        request_mapping["json_response_shape"] = {"type": "json_object"}

    return EndpointProfile.model_validate(
        {
            "id": "openai-chat-endpoint",
            "dialect": "openai_chat_v1",
            "base_url": "https://example.test/v1",
            "model": "opaque-model-id",
            "auth": {
                "kind": "bearer_env",
                "env_var": "MODEL_FINGERPRINT_API_KEY",
            },
            "capabilities": {
                "exposes_reasoning_text": True,
                "supports_json_object_response": supports_json_object_response,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_output_token_cap": True,
            },
            "request_mapping": request_mapping,
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
                "read_seconds": 120,
            },
            "retry_policy": {
                "max_attempts": 1,
                "retryable_statuses": [408, 429, 500, 502, 503, 504],
            },
        }
    )
class RecordingHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def _record_call(
        self,
        request,
        *,
        connect_timeout_seconds: int,
        read_timeout_seconds: int,
    ) -> None:
        self.calls.append(
            {
                "url": request.url,
                "body": dict(request.body),
                "connect_timeout_seconds": connect_timeout_seconds,
                "read_timeout_seconds": read_timeout_seconds,
            }
        )

    def send(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        self._record_call(
            request,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
        )
        return (
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": (
                                '{"task_result":{"owner":"Alice Wong"},'
                                '"evidence":{"owner":["e1"]},"unknowns":{},"violations":[]}'
                            ),
                            "reasoning_content": "1. comply with the grounded protocol",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 12,
                    "completion_tokens": 18,
                    "total_tokens": 54,
                    "completion_tokens_details": {"reasoning_tokens": 24},
                },
            },
            3210,
        )

    def start(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        self._record_call(
            request,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
        )

        class ImmediateHandle:
            def snapshot(self_nonlocal) -> HttpProgressSnapshot:
                return HttpProgressSnapshot(
                    bytes_received=192,
                    has_any_data=True,
                    elapsed_ms=3210,
                    first_byte_latency_ms=2000,
                    last_progress_latency_ms=3200,
                    completed=True,
                )

            def wait_until_terminal(
                self_nonlocal,
                timeout_seconds: float | None = None,
            ) -> HttpTerminalResult | None:
                return HttpTerminalResult(
                    payload={
                        "choices": [
                            {
                                "finish_reason": "stop",
                                "message": {
                                    "content": (
                                        '{"task_result":{"owner":"Alice Wong"},'
                                        '"evidence":{"owner":["e1"]},"unknowns":{},"violations":[]}'
                                    ),
                                    "reasoning_content": "1. comply with the grounded protocol",
                                },
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 12,
                            "completion_tokens": 18,
                            "total_tokens": 54,
                            "completion_tokens_details": {"reasoning_tokens": 24},
                        },
                    },
                    latency_ms=3210,
                    error=None,
                )

            def cancel(self_nonlocal) -> None:
                return None

        return ImmediateHandle()


def test_live_runner_preserves_messages_and_output_token_cap_field_exactly() -> None:
    prompt = build_prompt()
    original_messages = [message.model_dump(mode="json") for message in prompt.messages]
    client = RecordingHttpClient()
    runner = LiveRunner(
        endpoint=build_endpoint(
            supports_json_object_response=True,
            output_token_cap_field="max_completion_tokens",
        ),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=None,
        runtime_policy=resolve_runtime_policy(
            capability_probe_payload={
                "results": {
                    "thinking": {
                        "status": "accepted_but_ignored",
                    }
                }
            },
            supports_output_token_cap=True,
        ),
    )

    runner.execute(prompt)

    assert client.calls[0]["body"]["max_completion_tokens"] == 3000
    assert client.calls[0]["read_timeout_seconds"] == 120
    assert client.calls[0]["body"]["messages"] == original_messages
    assert [message.model_dump(mode="json") for message in prompt.messages] == original_messages
