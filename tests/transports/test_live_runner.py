from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.extractors.registry import build_default_registry
from modelfingerprint.services.feature_pipeline import FeaturePipeline
from modelfingerprint.services.runtime_policy import resolve_runtime_policy
from modelfingerprint.transports.http_client import (
    HttpClientError,
    HttpProgressSnapshot,
    HttpTerminalResult,
)
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


def build_endpoint() -> EndpointProfile:
    return EndpointProfile.model_validate(
        {
            "id": "siliconflow-openai-chat",
            "dialect": "openai_chat_v1",
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "Pro/zai-org/GLM-5",
            "auth": {
                "kind": "bearer_env",
                "env_var": "MODEL_FINGERPRINT_API_KEY",
            },
            "capabilities": {
                "exposes_reasoning_text": True,
                "supports_json_object_response": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_output_token_cap": True,
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
                "read_seconds": 120,
            },
            "retry_policy": {
                "max_attempts": 3,
                "retryable_statuses": [408, 429, 500, 502, 503, 504],
            },
        }
    )


def build_runtime_policy(
    thinking_status: str,
    *,
    endpoint: EndpointProfile | None = None,
):
    resolved_endpoint = endpoint or build_endpoint()
    return resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": thinking_status,
                }
            }
        },
        supports_output_token_cap=resolved_endpoint.capabilities.supports_output_token_cap,
    )


@dataclass(frozen=True)
class ScriptedStep:
    timeout_seconds: float
    snapshot: HttpProgressSnapshot
    terminal: HttpTerminalResult | None = None


class ScriptedHandle:
    def __init__(self, steps: list[ScriptedStep]) -> None:
        self._steps = list(steps)
        self._current_snapshot = HttpProgressSnapshot(
            bytes_received=0,
            has_any_data=False,
            elapsed_ms=0,
            completed=False,
        )
        self.wait_calls: list[float] = []
        self.cancelled = False

    def snapshot(self) -> HttpProgressSnapshot:
        return self._current_snapshot

    def wait_until_terminal(
        self,
        timeout_seconds: float | None = None,
    ) -> HttpTerminalResult | None:
        assert timeout_seconds is not None
        self.wait_calls.append(timeout_seconds)
        step = self._steps.pop(0)
        assert step.timeout_seconds == timeout_seconds
        self._current_snapshot = step.snapshot
        return step.terminal

    def cancel(self) -> None:
        self.cancelled = True


class ScriptedProgressHttpClient:
    def __init__(self, handles: list[ScriptedHandle]) -> None:
        self.calls: list[dict[str, object]] = []
        self._handles = list(handles)

    def start(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        self.calls.append(
            {
                "url": request.url,
                "headers": dict(request.headers),
                "body": dict(request.body),
                "connect_timeout_seconds": connect_timeout_seconds,
                "read_timeout_seconds": read_timeout_seconds,
            }
        )
        return self._handles.pop(0)


def successful_terminal(
    *,
    answer_text: str = '{"answer":"yes","confidence":"high"}',
    reasoning_text: str | None = "1. check the request\n2. answer in strict json",
    latency_ms: int = 42000,
) -> HttpTerminalResult:
    return HttpTerminalResult(
        payload={
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": answer_text,
                        "reasoning_content": reasoning_text,
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 18,
                "total_tokens": 54,
                "completion_tokens_details": {
                    "reasoning_tokens": 24 if reasoning_text else 0,
                },
            },
        },
        latency_ms=latency_ms,
        error=None,
    )


def test_live_runner_switches_to_progress_polling_without_resending_prompt(
    tmp_path: Path,
) -> None:
    handle = ScriptedHandle(
        [
            ScriptedStep(
                timeout_seconds=30.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=0,
                    has_any_data=False,
                    elapsed_ms=30000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=30.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=192,
                    has_any_data=True,
                    elapsed_ms=60000,
                    first_byte_latency_ms=41000,
                    last_progress_latency_ms=59000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=10.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=384,
                    has_any_data=True,
                    elapsed_ms=70000,
                    first_byte_latency_ms=41000,
                    last_progress_latency_ms=69000,
                    completed=True,
                ),
                terminal=successful_terminal(latency_ms=70000),
            ),
        ]
    )
    client = ScriptedProgressHttpClient([handle])
    trace_dir = tmp_path / "traces" / "run-progress"
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=trace_dir,
        runtime_policy=build_runtime_policy("supported"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert len(client.calls) == 1
    assert client.calls[0]["body"]["max_tokens"] == 3000
    assert client.calls[0]["read_timeout_seconds"] == 120
    assert handle.wait_calls == [30.0, 30.0, 10.0]
    assert len(result.attempts) == 1
    assert result.attempts[0].request_attempt_index == 1
    assert result.attempts[0].bytes_received == 384
    assert result.attempts[0].first_byte_latency_ms == 41000
    assert result.attempts[0].completed is True
    assert (trace_dir / "p003.request.json").exists()
    assert (trace_dir / "p003.response.json").exists()

    request_trace = json.loads((trace_dir / "p003.request.json").read_text())
    assert request_trace["headers"]["Authorization"] == "Bearer ***REDACTED***"


def test_live_runner_times_out_non_thinking_prompt_after_first_silent_checkpoint() -> None:
    handle = ScriptedHandle(
        [
            ScriptedStep(
                timeout_seconds=30.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=0,
                    has_any_data=False,
                    elapsed_ms=30000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=2.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=0,
                    has_any_data=False,
                    elapsed_ms=30010,
                    completed=False,
                    terminal_error_kind="cancelled",
                ),
                terminal=HttpTerminalResult(
                    payload=None,
                    latency_ms=None,
                    error=HttpClientError(kind="cancelled", message="request cancelled"),
                ),
            ),
        ]
    )
    client = ScriptedProgressHttpClient([handle])
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=None,
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "timeout"
    assert len(client.calls) == 1
    assert handle.wait_calls == [30.0, 2.0]
    assert handle.cancelled is True
    assert result.error is not None
    assert result.error.kind == "no_data_checkpoint_exceeded"
    assert result.attempts[0].abort_reason == "no_data_checkpoint_exceeded"
    assert result.attempts[0].completed is False


def test_live_runner_aborts_after_total_deadline_when_partial_response_never_finishes() -> None:
    handle = ScriptedHandle(
        [
            ScriptedStep(
                timeout_seconds=30.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=128,
                    has_any_data=True,
                    elapsed_ms=30000,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=29000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=10.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=192,
                    has_any_data=True,
                    elapsed_ms=40000,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=39000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=10.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=256,
                    has_any_data=True,
                    elapsed_ms=120000,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=119000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=2.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=256,
                    has_any_data=True,
                    elapsed_ms=120001,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=119000,
                    completed=False,
                    terminal_error_kind="cancelled",
                ),
                terminal=HttpTerminalResult(
                    payload=None,
                    latency_ms=None,
                    error=HttpClientError(kind="cancelled", message="request cancelled"),
                ),
            ),
        ]
    )
    client = ScriptedProgressHttpClient([handle])
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=None,
        runtime_policy=build_runtime_policy("supported"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "timeout"
    assert len(client.calls) == 1
    assert handle.wait_calls == [30.0, 10.0, 10.0, 2.0]
    assert handle.cancelled is True
    assert result.error is not None
    assert result.error.kind == "total_deadline_exceeded"
    assert result.attempts[0].abort_reason == "total_deadline_exceeded"
    assert result.attempts[0].bytes_received == 256


def test_feature_pipeline_preserves_progress_attempt_metadata(tmp_path: Path) -> None:
    handle = ScriptedHandle(
        [
            ScriptedStep(
                timeout_seconds=30.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=96,
                    has_any_data=True,
                    elapsed_ms=30000,
                    first_byte_latency_ms=21000,
                    last_progress_latency_ms=29000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=10.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=240,
                    has_any_data=True,
                    elapsed_ms=40000,
                    first_byte_latency_ms=21000,
                    last_progress_latency_ms=39000,
                    completed=True,
                ),
                terminal=successful_terminal(latency_ms=40000),
            ),
        ]
    )
    client = ScriptedProgressHttpClient([handle])
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-2",
        runtime_policy=build_runtime_policy("supported"),
    )
    execution = runner.execute(build_prompt())

    artifact = FeaturePipeline(build_default_registry(ROOT / "extractors")).build_run_artifact(
        run_id="suspect-a.fingerprint-suite-v1",
        suite_id="fingerprint-suite-v1",
        target_label="suspect-a",
        claimed_model=None,
        executions=[execution],
    )

    assert artifact.prompt_count_total == 1
    assert artifact.prompt_count_completed == 1
    assert artifact.prompt_count_scoreable == 1
    assert artifact.answer_coverage_ratio == 1.0
    assert artifact.reasoning_coverage_ratio == 1.0
    assert artifact.prompts[0].request_snapshot is not None
    assert artifact.prompts[0].completion is not None
    assert artifact.prompts[0].completion.reasoning_visible is True
    assert artifact.prompts[0].attempts
    assert artifact.prompts[0].attempts[0].read_timeout_seconds == 120
    assert artifact.prompts[0].attempts[0].request_attempt_index == 1
    assert artifact.prompts[0].attempts[0].bytes_received == 240
