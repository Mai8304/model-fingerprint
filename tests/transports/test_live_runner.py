from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.dialects.base import HttpRequestSpec
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.extractors.base import ExtractorDescriptor
from modelfingerprint.extractors.registry import ExtractorRegistry
from modelfingerprint.services.feature_pipeline import FeaturePipeline
from modelfingerprint.services.runtime_policy import resolve_runtime_policy
from modelfingerprint.transports.http_client import (
    HttpClientError,
    HttpProgressSnapshot,
    HttpTerminalResult,
)
from modelfingerprint.transports.live_runner import LiveRunner


def build_prompt() -> PromptDefinition:
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


def build_prompt_with_id(prompt_id: str) -> PromptDefinition:
    return build_prompt().model_copy(update={"id": prompt_id, "name": prompt_id})


def build_endpoint(
    *,
    endpoint_id: str = "siliconflow-openai-chat",
    provider_id: str | None = None,
    model: str = "Pro/zai-org/GLM-5",
    runtime_profile_id: str | None = None,
) -> EndpointProfile:
    return EndpointProfile.model_validate(
        {
            "id": endpoint_id,
            "dialect": "openai_chat_v1",
            "protocol_family": "openai_compatible",
            "provider_id": provider_id,
            "runtime_profile_id": runtime_profile_id,
            "base_url": "https://api.siliconflow.cn/v1",
            "model": model,
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


def build_openrouter_endpoint(model: str = "z-ai/glm-4.7") -> EndpointProfile:
    return build_endpoint().model_copy(
        update={
            "base_url": "https://openrouter.ai/api/v1",
            "model": model,
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
        endpoint=resolved_endpoint,
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


class ScriptedBlockingHttpClient:
    def __init__(self, payload: dict[str, object], *, latency_ms: int) -> None:
        self.calls: list[dict[str, object]] = []
        self._payload = payload
        self._latency_ms = latency_ms

    def send(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        self.calls.append(
            {
                "url": request.url,
                "headers": dict(request.headers),
                "body": dict(request.body),
                "connect_timeout_seconds": connect_timeout_seconds,
                "read_timeout_seconds": read_timeout_seconds,
            }
        )
        return self._payload, self._latency_ms


class ScriptedBlockingSequenceHttpClient:
    def __init__(self, responses: list[tuple[dict[str, object], int]]) -> None:
        self.calls: list[dict[str, object]] = []
        self._responses = list(responses)

    def send(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        self.calls.append(
            {
                "url": request.url,
                "headers": dict(request.headers),
                "body": dict(request.body),
                "connect_timeout_seconds": connect_timeout_seconds,
                "read_timeout_seconds": read_timeout_seconds,
            }
        )
        payload, latency_ms = self._responses.pop(0)
        return payload, latency_ms


class TimeoutFailingHttpClient:
    def send(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        raise HttpClientError(
            kind="first_byte_timeout",
            message="response did not arrive before the first byte deadline",
        )


class StreamingOpenAIChatDialectAdapter(OpenAIChatDialectAdapter):
    def build_request(self, *args, **kwargs) -> HttpRequestSpec:
        request = super().build_request(*args, **kwargs)
        headers = dict(request.headers)
        headers["Accept"] = "text/event-stream"
        body = dict(request.body)
        body["stream"] = True
        return HttpRequestSpec(url=request.url, headers=headers, body=body)

def build_test_registry() -> ExtractorRegistry:
    return ExtractorRegistry(
        descriptors={
            "evidence_grounding_v3": ExtractorDescriptor.model_validate(
                {
                    "name": "evidence_grounding_v3",
                    "family": "evidence_grounding",
                    "version": 3,
                    "features": ["owner"],
                }
            ),
            "reasoning_trace_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "reasoning_trace_v1",
                    "family": "evidence_grounding",
                    "version": 1,
                    "features": ["steps"],
                }
            ),
            "completion_metadata_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "completion_metadata_v1",
                    "family": "evidence_grounding",
                    "version": 1,
                    "features": ["finish_reason"],
                }
            ),
        },
        handlers={
            "evidence_grounding_v3": lambda canonical_output: {"owner": "Alice Wong"},
            "reasoning_trace_v1": lambda reasoning_text: {"steps": 2},
            "completion_metadata_v1": lambda completion: {
                "finish_reason": completion.finish_reason or "stop"
            },
        },
    )
def successful_terminal(
    *,
    answer_text: str = (
        '{"task_result":{"owner":"Alice Wong"},"evidence":{"owner":["e1"]},"unknowns":{},"violations":[]}'
    ),
    reasoning_text: str | None = "1. check the request\n2. answer in grounded json",
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


def test_live_runner_uses_blocking_send_for_non_streaming_runtime_policy_requests(
    tmp_path: Path,
) -> None:
    terminal = successful_terminal(latency_ms=70000)
    assert terminal.payload is not None
    client = ScriptedBlockingHttpClient(terminal.payload, latency_ms=70000)
    trace_dir = tmp_path / "traces" / "run-blocking"
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=trace_dir,
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert len(client.calls) == 1
    assert client.calls[0]["headers"]["Accept"] == "application/json"
    assert client.calls[0]["body"]["max_tokens"] == 500
    assert client.calls[0]["read_timeout_seconds"] == 90
    assert len(result.attempts) == 1
    assert result.attempts[0].runtime_intent == "structured_extraction"
    assert result.attempts[0].runtime_tier_index == 0
    assert result.attempts[0].first_byte_timeout_seconds == 30
    assert result.attempts[0].idle_timeout_seconds == 15
    assert result.attempts[0].total_deadline_seconds == 90
    assert result.attempts[0].latency_ms == 70000
    assert result.attempts[0].bytes_received is None
    assert result.attempts[0].completed is True
    assert (trace_dir / "p021.request.json").exists()
    assert (trace_dir / "p021.response.json").exists()


def test_live_runner_applies_kimi_structured_extraction_request_overrides(
    tmp_path: Path,
) -> None:
    terminal = successful_terminal(latency_ms=4800, reasoning_text=None)
    assert terminal.payload is not None
    client = ScriptedBlockingHttpClient(terminal.payload, latency_ms=4800)
    runner = LiveRunner(
        endpoint=build_endpoint(
            endpoint_id="moonshot-kimi-k2.5",
            provider_id="moonshot",
            model="kimi-k2.5",
            runtime_profile_id="structured_extraction_disable_thinking_v1",
        ),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-kimi-structured",
        runtime_policy=build_runtime_policy(
            "supported",
            endpoint=build_endpoint(
                endpoint_id="moonshot-kimi-k2.5",
                provider_id="moonshot",
                model="kimi-k2.5",
                runtime_profile_id="structured_extraction_disable_thinking_v1",
            ),
        ),
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert len(client.calls) == 1
    assert client.calls[0]["body"]["max_tokens"] == 500
    assert client.calls[0]["body"]["thinking"] == {"type": "disabled"}


def test_live_runner_treats_transport_timeout_kinds_as_timeout_status(
    tmp_path: Path,
) -> None:
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=TimeoutFailingHttpClient(),
        trace_dir=tmp_path / "traces" / "run-timeout-kind",
    )

    result = runner.execute(build_prompt())

    assert result.status == "timeout"
    assert result.error is not None
    assert result.error.kind == "first_byte_timeout"


def test_live_runner_switches_to_progress_polling_without_resending_prompt(
    tmp_path: Path,
) -> None:
    handle = ScriptedHandle(
        [
            ScriptedStep(
                timeout_seconds=30.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=192,
                    has_any_data=True,
                    elapsed_ms=30000,
                    first_byte_latency_ms=21000,
                    last_progress_latency_ms=29000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=15.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=384,
                    has_any_data=True,
                    elapsed_ms=45000,
                    first_byte_latency_ms=21000,
                    last_progress_latency_ms=44000,
                    completed=True,
                ),
                terminal=successful_terminal(latency_ms=45000),
            ),
        ]
    )
    client = ScriptedProgressHttpClient([handle])
    trace_dir = tmp_path / "traces" / "run-progress"
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=StreamingOpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=trace_dir,
        runtime_policy=build_runtime_policy("supported"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert len(client.calls) == 1
    assert client.calls[0]["body"]["max_tokens"] == 500
    assert client.calls[0]["body"]["stream"] is True
    assert client.calls[0]["read_timeout_seconds"] == 90
    assert handle.wait_calls == [30.0, 15.0]
    assert len(result.attempts) == 1
    assert result.attempts[0].request_attempt_index == 1
    assert result.attempts[0].runtime_intent == "structured_extraction"
    assert result.attempts[0].bytes_received == 384
    assert result.attempts[0].first_byte_latency_ms == 21000
    assert result.attempts[0].completed is True
    assert (trace_dir / "p021.request.json").exists()
    assert (trace_dir / "p021.response.json").exists()

    request_trace = json.loads((trace_dir / "p021.request.json").read_text())
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
        dialect=StreamingOpenAIChatDialectAdapter(),
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
    assert result.error.kind == "first_byte_timeout"
    assert result.attempts[0].abort_reason == "first_byte_timeout"
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
                timeout_seconds=15.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=192,
                    has_any_data=True,
                    elapsed_ms=45000,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=44000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=15.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=256,
                    has_any_data=True,
                    elapsed_ms=60000,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=59000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=15.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=320,
                    has_any_data=True,
                    elapsed_ms=75000,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=74000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=15.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=384,
                    has_any_data=True,
                    elapsed_ms=90000,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=89000,
                    completed=False,
                ),
            ),
            ScriptedStep(
                timeout_seconds=2.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=384,
                    has_any_data=True,
                    elapsed_ms=90001,
                    first_byte_latency_ms=25000,
                    last_progress_latency_ms=89000,
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
        dialect=StreamingOpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=None,
        runtime_policy=build_runtime_policy("supported"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "timeout"
    assert len(client.calls) == 1
    assert handle.wait_calls == [30.0, 15.0, 15.0, 15.0, 15.0, 2.0]
    assert handle.cancelled is True
    assert result.error is not None
    assert result.error.kind == "total_deadline_exceeded"
    assert result.attempts[0].abort_reason == "total_deadline_exceeded"
    assert result.attempts[0].bytes_received == 384


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
                timeout_seconds=15.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=240,
                    has_any_data=True,
                    elapsed_ms=45000,
                    first_byte_latency_ms=21000,
                    last_progress_latency_ms=44000,
                    completed=True,
                ),
                terminal=successful_terminal(latency_ms=45000),
            ),
        ]
    )
    client = ScriptedProgressHttpClient([handle])
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=StreamingOpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-2",
        runtime_policy=build_runtime_policy("supported"),
    )
    execution = runner.execute(build_prompt())

    artifact = FeaturePipeline(build_test_registry()).build_run_artifact(
        run_id="suspect-a.fingerprint-suite-v3",
        suite_id="fingerprint-suite-v3",
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
    assert artifact.prompts[0].attempts[0].read_timeout_seconds == 90
    assert artifact.prompts[0].attempts[0].request_attempt_index == 1
    assert artifact.prompts[0].attempts[0].runtime_intent == "structured_extraction"
    assert artifact.prompts[0].attempts[0].bytes_received == 240


def test_live_runner_accepts_structured_answer_recovered_from_reasoning() -> None:
    handle = ScriptedHandle(
        [
            ScriptedStep(
                timeout_seconds=30.0,
                snapshot=HttpProgressSnapshot(
                    bytes_received=160,
                    has_any_data=True,
                    elapsed_ms=30000,
                    first_byte_latency_ms=22000,
                    last_progress_latency_ms=29000,
                    completed=True,
                ),
                terminal=HttpTerminalResult(
                    payload={
                        "choices": [
                            {
                                "finish_reason": "length",
                                "message": {
                                    "content": None,
                                    "reasoning": (
                                        "analysis\n```json\n"
                                        '{"task_result":{"owner":"Alice Wong"},"evidence":{"owner":["e1"]},"unknowns":{},"violations":[]}\n'
                                        "```\nextra tail"
                                    ),
                                },
                            }
                        ],
                        "usage": {
                            "prompt_tokens": 12,
                            "completion_tokens": 18,
                            "total_tokens": 54,
                            "completion_tokens_details": {
                                "reasoning_tokens": 24,
                            },
                        },
                    },
                    latency_ms=60000,
                    error=None,
                ),
            ),
        ]
    )
    client = ScriptedProgressHttpClient([handle])
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=StreamingOpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=None,
        runtime_policy=build_runtime_policy("supported"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert result.error is None
    assert result.attempts[0].read_timeout_seconds == 90
    assert (
        result.raw_output
        == '{"task_result":{"owner":"Alice Wong"},"evidence":{"owner":["e1"]},"unknowns":{},"violations":[]}'
    )
    assert result.completion is not None
    assert result.completion.reasoning_visible is True
    assert result.completion.finish_reason == "length"


def test_live_runner_escalates_structured_extraction_tiers_only_after_explicit_failure_signals(
) -> None:
    client = ScriptedBlockingSequenceHttpClient(
        [
            (
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": "",
                                "reasoning_content": "need more room",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 8,
                        "total_tokens": 20,
                    },
                },
                1200,
            ),
            (
                {
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {
                                "content": "not json at all",
                                "reasoning_content": "still missing structure",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 16,
                        "total_tokens": 28,
                    },
                },
                1600,
            ),
            (
                successful_terminal(latency_ms=2200).payload,
                2200,
            ),
        ]
    )
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=None,
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert [call["body"]["max_tokens"] for call in client.calls] == [500, 1500, 3000]
    assert [call["read_timeout_seconds"] for call in client.calls] == [90, 120, 120]
    assert len(result.attempts) == 3
    assert result.attempts[0].status == "invalid_response"
    assert result.attempts[0].error_kind == "missing_answer_text"
    assert result.attempts[1].status == "invalid_response"
    assert result.attempts[1].error_kind == "invalid_structured_output"
    assert result.attempts[2].status == "completed"
    assert result.attempts[2].runtime_tier_index == 2


def test_live_runner_retries_timeout_into_next_structured_extraction_tier() -> None:
    client = ScriptedBlockingSequenceHttpClient(
        [
            (
                successful_terminal(
                    answer_text=(
                        '{"task_result":{"owner":"Alice Wong"},"evidence":{"owner":["e1"]},"unknowns":{},"violations":[]}'
                    ),
                    latency_ms=2100,
                ).payload,
                2100,
            ),
        ]
    )

    class TimeoutThenSuccessHttpClient:
        def __init__(self, fallback: ScriptedBlockingSequenceHttpClient) -> None:
            self.calls: list[dict[str, object]] = []
            self._fallback = fallback
            self._timeout_count = 0

        def send(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
            self.calls.append(
                {
                    "url": request.url,
                    "headers": dict(request.headers),
                    "body": dict(request.body),
                    "connect_timeout_seconds": connect_timeout_seconds,
                    "read_timeout_seconds": read_timeout_seconds,
                }
            )
            if self._timeout_count < 3:
                self._timeout_count += 1
                raise HttpClientError(
                    kind="total_deadline_exceeded",
                    message="request did not complete before the total deadline",
                )
            return self._fallback.send(
                request,
                connect_timeout_seconds=connect_timeout_seconds,
                read_timeout_seconds=read_timeout_seconds,
            )

    http_client = TimeoutThenSuccessHttpClient(client)
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=http_client,
        trace_dir=None,
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert [call["body"]["max_tokens"] for call in http_client.calls] == [500, 500, 500, 1500]
    assert [call["read_timeout_seconds"] for call in http_client.calls] == [90, 90, 90, 120]
    assert len(result.attempts) == 2
    assert result.attempts[0].status == "timeout"
    assert result.attempts[0].error_kind == "total_deadline_exceeded"
    assert result.attempts[1].status == "completed"
    assert result.attempts[1].runtime_tier_index == 1


def test_live_runner_retries_p033_when_partial_payload_omits_task_result(
    tmp_path: Path,
) -> None:
    client = ScriptedBlockingSequenceHttpClient(
        responses=[
            (
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {
                                "content": '{"evidence":{"q1":["e1"],"q3":["e3"]}}',
                                "reasoning_content": "partial abstention payload",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 18,
                        "total_tokens": 30,
                    },
                },
                1100,
            ),
            (
                successful_terminal(
                    answer_text=(
                        '{"task_result":{"q1":{"status":"answer","value":"yes"},'
                        '"q2":{"status":"unknown","value":null},'
                        '"q3":{"status":"answer","value":"Mara Singh"},'
                        '"q4":{"status":"conflict_unresolved","value":null}},'
                        '"evidence":{"q1":["e1"],"q3":["e3"]},"unknowns":["q2","q4"],"violations":[]}'
                    ),
                    latency_ms=1700,
                ).payload,
                1700,
            ),
        ]
    )
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p033-validation",
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt_with_id("p033"))

    assert result.status == "completed"
    assert [call["body"]["max_tokens"] for call in client.calls] == [500, 1500]
    assert len(result.attempts) == 2
    assert result.attempts[0].status == "invalid_response"
    assert result.attempts[0].error_kind == "invalid_structured_output"
    assert result.attempts[1].status == "completed"


def test_live_runner_retries_p032_when_partial_payload_omits_task_result(
    tmp_path: Path,
) -> None:
    client = ScriptedBlockingSequenceHttpClient(
        responses=[
            (
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {
                                "content": "{}",
                                "reasoning_content": "partial retrieval payload",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 18,
                        "total_tokens": 30,
                    },
                },
                1050,
            ),
            (
                successful_terminal(
                    answer_text=(
                        '{"task_result":{"found_entities":["Arbor","Beacon","Cinder","Drift"],'
                        '"excluded_entities":["Arbor-review","Harbor shadow","Beacon Ops","Project Cinder","Drift-east"]},'
                        '"evidence":{"paragraph_map":{"Arbor":"p1","Beacon":"p2","Cinder":"p2","Drift":"p3"}},'
                        '"unknowns":{},"violations":[]}'
                    ),
                    latency_ms=1650,
                ).payload,
                1650,
            ),
        ]
    )
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p032-validation",
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt_with_id("p032"))

    assert result.status == "completed"
    assert [call["body"]["max_tokens"] for call in client.calls] == [500, 1500]
    assert len(result.attempts) == 2
    assert result.attempts[0].status == "invalid_response"
    assert result.attempts[0].error_kind == "invalid_structured_output"
    assert result.attempts[1].status == "completed"


def test_live_runner_retries_p031_when_partial_payload_omits_task_result(
    tmp_path: Path,
) -> None:
    client = ScriptedBlockingSequenceHttpClient(
        responses=[
            (
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {
                                "content": '{"owner":"Elena Park","role":"Principal SRE","region":null,"change_window":"2026-04-06 01:30 UTC"}',
                                "reasoning_content": "partial grounding payload",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 18,
                        "total_tokens": 30,
                    },
                },
                1000,
            ),
            (
                successful_terminal(
                    answer_text=(
                        '{"task_result":{"owner":"Elena Park","role":"Principal SRE","region":null,'
                        '"change_window":"2026-04-06 01:30 UTC"},'
                        '"evidence":{"owner":["e2"],"role":["e3"],"region":[],"change_window":["e8"]},'
                        '"unknowns":{"region":"no_evidence"},"violations":[]}'
                    ),
                    latency_ms=1600,
                ).payload,
                1600,
            ),
        ]
    )
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p031-validation",
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt_with_id("p031"))

    assert result.status == "completed"
    assert [call["body"]["max_tokens"] for call in client.calls] == [500, 1500]
    assert len(result.attempts) == 2
    assert result.attempts[0].status == "invalid_response"
    assert result.attempts[0].error_kind == "invalid_structured_output"
    assert result.attempts[1].status == "completed"


def test_live_runner_retries_p034_when_partial_payload_omits_task_result(
    tmp_path: Path,
) -> None:
    client = ScriptedBlockingSequenceHttpClient(
        responses=[
            (
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {
                                "content": '{"evidence":{"derivation_codes":{"ticket_a":"r4","worker_x":"r7"}}}',
                                "reasoning_content": "partial state tracking payload",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 18,
                        "total_tokens": 30,
                    },
                },
                1200,
            ),
            (
                successful_terminal(
                    answer_text=(
                        '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
                        '"worker_x":{"status":"suspended","owner":"ops","priority":"p3"}},'
                        '"evidence":{"derivation_codes":{"ticket_a":"r4","worker_x":"r7"},"defaults_used":[]},'
                        '"unknowns":{},"violations":[]}'
                    ),
                    latency_ms=1800,
                ).payload,
                1800,
            ),
        ]
    )
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p034-validation",
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt_with_id("p034"))

    assert result.status == "completed"
    assert [call["body"]["max_tokens"] for call in client.calls] == [500, 1500]
    assert len(result.attempts) == 2
    assert result.attempts[0].status == "invalid_response"
    assert result.attempts[0].error_kind == "invalid_structured_output"
    assert result.attempts[1].status == "completed"


def test_live_runner_uses_prompt_specific_openrouter_budget_and_reasoning_override(
    tmp_path: Path,
) -> None:
    terminal = successful_terminal(
        answer_text=(
            '{"task_result":{"q1":{"status":"answer","value":"yes"},'
            '"q2":{"status":"unknown","value":null},'
            '"q3":{"status":"answer","value":"Mara Singh"},'
            '"q4":{"status":"conflict_unresolved","value":null}},'
            '"evidence":{"q1":["e1"],"q3":["e3"]},"unknowns":["q2","q4"],"violations":[]}'
        ),
        latency_ms=2600,
        reasoning_text=None,
    )
    assert terminal.payload is not None
    client = ScriptedBlockingHttpClient(terminal.payload, latency_ms=2600)
    runner = LiveRunner(
        endpoint=build_openrouter_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p033-openrouter-budget",
        runtime_policy=build_runtime_policy(
            "accepted_but_ignored",
            endpoint=build_openrouter_endpoint(),
        ),
    )

    result = runner.execute(build_prompt_with_id("p033"))

    assert result.status == "completed"
    assert len(client.calls) == 1
    assert client.calls[0]["body"]["max_tokens"] == 3000
    assert client.calls[0]["body"]["reasoning"] == {"effort": "minimal", "exclude": True}


def test_live_runner_uses_prompt_specific_openrouter_budget_and_reasoning_override_for_p032(
    tmp_path: Path,
) -> None:
    terminal = successful_terminal(
        answer_text=(
            '{"task_result":{"found_entities":["Arbor","Beacon","Cinder","Drift"],'
            '"excluded_entities":["Arbor-review","Harbor shadow","Beacon Ops","Project Cinder","Drift-east"]},'
            '"evidence":{"paragraph_map":{"Arbor":"p1","Beacon":"p2","Cinder":"p2","Drift":"p3"}},'
            '"unknowns":{},"violations":[]}'
        ),
        latency_ms=2500,
        reasoning_text=None,
    )
    assert terminal.payload is not None
    client = ScriptedBlockingHttpClient(terminal.payload, latency_ms=2500)
    runner = LiveRunner(
        endpoint=build_openrouter_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p032-openrouter-budget",
        runtime_policy=build_runtime_policy(
            "accepted_but_ignored",
            endpoint=build_openrouter_endpoint(),
        ),
    )

    result = runner.execute(build_prompt_with_id("p032"))

    assert result.status == "completed"
    assert len(client.calls) == 1
    assert client.calls[0]["body"]["max_tokens"] == 3000
    assert client.calls[0]["body"]["reasoning"] == {"effort": "minimal", "exclude": True}


def test_live_runner_uses_prompt_specific_openrouter_budget_and_reasoning_override_for_p031(
    tmp_path: Path,
) -> None:
    terminal = successful_terminal(
        answer_text=(
            '{"task_result":{"owner":"Elena Park","role":"Principal SRE","region":null,'
            '"change_window":"2026-04-06 01:30 UTC"},'
            '"evidence":{"owner":["e2"],"role":["e3"],"region":[],"change_window":["e8"]},'
            '"unknowns":{"region":"no_evidence"},"violations":[]}'
        ),
        latency_ms=2400,
        reasoning_text=None,
    )
    assert terminal.payload is not None
    client = ScriptedBlockingHttpClient(terminal.payload, latency_ms=2400)
    runner = LiveRunner(
        endpoint=build_openrouter_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p031-openrouter-budget",
        runtime_policy=build_runtime_policy(
            "accepted_but_ignored",
            endpoint=build_openrouter_endpoint(),
        ),
    )

    result = runner.execute(build_prompt_with_id("p031"))

    assert result.status == "completed"
    assert len(client.calls) == 1
    assert client.calls[0]["body"]["max_tokens"] == 3000
    assert client.calls[0]["body"]["reasoning"] == {"effort": "minimal", "exclude": True}


def test_live_runner_retries_p035_when_placeholder_mentions_pass_shape_but_not_schema(
    tmp_path: Path,
) -> None:
    client = ScriptedBlockingSequenceHttpClient(
        responses=[
            (
                {
                    "choices": [
                        {
                            "finish_reason": "length",
                            "message": {
                                "content": (
                                    '{"task_result":{"canonical_entities":["id1","id2"],'
                                    '"alias_map":{"mention1":"id1","mention2":"id1","mention3":"id2","mention4":"id2"},'
                                    '"ambiguous_mentions":["mention5","mention6"],'
                                    '"rejected_items":["mention7","mention8","mention9","mention10"]},'
                                    '"evidence":{},"unknowns":{},"violations":[]}'
                                ),
                                "reasoning_content": "placeholder alignment payload",
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 18,
                        "total_tokens": 30,
                    },
                },
                1200,
            ),
            (
                successful_terminal(
                    answer_text=(
                        '{"task_result":{"canonical_entities":["openwhale_control","atlas_db_east"],'
                        '"alias_map":{"OpenWhale Control Plane":"openwhale_control","OW Control":"openwhale_control",'
                        '"Atlas East DB":"atlas_db_east","atlas-db-east":"atlas_db_east"},'
                        '"ambiguous_mentions":["OW","Atlas"],'
                        '"rejected_items":["Project Mercury","mercury-cutover","control","staging-note"]},'
                        '"evidence":{},"unknowns":{},"violations":[]}'
                    ),
                    latency_ms=1800,
                ).payload,
                1800,
            ),
        ]
    )
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=tmp_path / "traces" / "run-p035-validation",
        runtime_policy=build_runtime_policy("accepted_but_ignored"),
    )

    result = runner.execute(build_prompt_with_id("p035"))

    assert result.status == "completed"
    assert [call["body"]["max_tokens"] for call in client.calls] == [500, 1500]
    assert len(result.attempts) == 2
    assert result.attempts[0].status == "invalid_response"
    assert result.attempts[0].error_kind == "invalid_structured_output"
    assert result.attempts[1].status == "completed"
