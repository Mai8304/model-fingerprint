from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import RunArtifact, UsageMetadata
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.services.feature_pipeline import PromptExecutionResult
from modelfingerprint.services.runtime_policy import resolve_runtime_policy
from modelfingerprint.services.suite_runner import SuiteRunner
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.transports.http_client import HttpProgressSnapshot, HttpTerminalResult
from modelfingerprint.transports.live_runner import LiveRunner

ROOT = Path(__file__).resolve().parents[2]


def build_prompt() -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p003",
            "name": "fixed_json_triage",
            "family": "strict_format",
            "intent": "detect strict JSON obedience",
            "messages": [
                {
                    "role": "system",
                    "content": "Return only the requested JSON object.",
                },
                {
                    "role": "user",
                    "content": (
                        'Reply with JSON only using fields "answer" and "confidence" '
                        "in that order."
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
            "output_contract": {"id": "strict_json_v2", "canonicalizer": "strict_json_v2"},
            "extractors": {
                "answer": "strict_format_v1",
                "reasoning": "reasoning_trace_v1",
                "transport": "completion_metadata_v1",
            },
            "required_capabilities": ["chat_completions", "json_object_response"],
            "weight_hint": 0.9,
            "tags": ["format", "json"],
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


class RecordingTransport:
    def __init__(self, endpoint: EndpointProfile) -> None:
        self.endpoint = endpoint
        self.called_prompt_ids: list[str] = []

    def execute(self, prompt: PromptDefinition) -> PromptExecutionResult:
        payloads = {
            "p021": (
                '{"task_result":{"owner":"Alice Wong","role":"Primary DBA","region":null,'
                '"change_window":"2026-03-21 02:00 UTC"},'
                '"evidence":{"owner":["e3"],"role":["e2"],"region":[],"change_window":["e5"]},'
                '"unknowns":{"region":"insufficient_evidence"},"violations":[]}'
            ),
            "p023": (
                '{"task_result":{"q1":{"status":"answer","value":"yes"},'
                '"q2":{"status":"unknown","value":null},'
                '"q3":{"status":"answer","value":"retry failed background jobs"},'
                '"q4":{"status":"conflict_unresolved","value":null}},'
                '"evidence":{"q1":["e1"],"q2":["e5"],"q3":["e1"],"q4":["e3","e4"]},'
                '"unknowns":{"q2":"missing_actor","q4":"conflicting_notes"},"violations":[]}'
            ),
            "p024": (
                '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
                '"ticket_b":{"status":"open","owner":"db","priority":"p2"},'
                '"worker_x":{"status":"suspended","owner":"ml","priority":"p3"}},'
                '"evidence":{"derivation_codes":{"ticket_a":"r5","ticket_b":"r6","worker_x":"r10"},'
                '"defaults_used":["ticket_b.priority"]},"unknowns":{},"violations":[]}'
            ),
        }
        self.called_prompt_ids.append(prompt.id)
        return PromptExecutionResult(
            prompt=prompt,
            raw_output=payloads[prompt.id],
            usage=UsageMetadata(input_tokens=10, output_tokens=5, total_tokens=15),
        )


class RecordingHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def start(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        self.calls.append(
            {
                "url": request.url,
                "body": dict(request.body),
                "connect_timeout_seconds": connect_timeout_seconds,
                "read_timeout_seconds": read_timeout_seconds,
            }
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
                                    "content": '{"answer":"yes","confidence":"high"}',
                                    "reasoning_content": "1. comply with the fixed protocol",
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


def test_suite_runner_executes_all_v3_prompts_without_adapting_the_suite(
    tmp_path: Path,
) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")

    transport = RecordingTransport(
        build_endpoint(
            supports_json_object_response=False,
            output_token_cap_field="max_tokens",
        )
    )
    runner = SuiteRunner(
        paths=RepositoryPaths(root=tmp_path),
        transport=transport,
    )

    output_path = runner.run_suite(
        suite_id="quick-check-v3",
        target_label="suspect-a",
        claimed_model=None,
        run_date=date(2026, 3, 9),
    )

    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    assert transport.called_prompt_ids == ["p021", "p023", "p024"]
    prompt_statuses = {prompt.prompt_id: prompt.status for prompt in artifact.prompts}
    assert prompt_statuses["p021"] == "completed"
    assert prompt_statuses["p023"] == "completed"
    assert prompt_statuses["p024"] == "completed"


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
