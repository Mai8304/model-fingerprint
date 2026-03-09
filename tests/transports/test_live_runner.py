from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.extractors.registry import build_default_registry
from modelfingerprint.services.feature_pipeline import FeaturePipeline
from modelfingerprint.transports.http_client import HttpClientError
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


class FakeHttpClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self._attempt = 0

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
        self._attempt += 1
        if self._attempt == 1:
            raise HttpClientError(kind="http_status", message="rate limited", status_code=429)
        return (
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '{"answer":"yes","confidence":"high"}',
                            "reasoning_content": "1. check the request\n2. answer in strict json",
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
            18342,
        )


def test_live_runner_retries_retryable_errors_and_persists_traces(tmp_path: Path) -> None:
    client = FakeHttpClient()
    trace_dir = tmp_path / "traces" / "run-1"
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=trace_dir,
    )

    result = runner.execute(build_prompt())

    assert result.status == "completed"
    assert result.raw_output == '{"answer":"yes","confidence":"high"}'
    assert result.completion is not None
    assert result.completion.usage.reasoning_tokens == 24
    assert len(client.calls) == 2
    assert client.calls[0]["body"]["max_tokens"] == 96
    assert client.calls[1]["body"]["max_tokens"] == 96
    assert (trace_dir / "p003.request.json").exists()
    assert (trace_dir / "p003.response.json").exists()

    request_trace = json.loads((trace_dir / "p003.request.json").read_text())
    assert request_trace["headers"]["Authorization"] == "Bearer ***REDACTED***"


def test_feature_pipeline_preserves_live_runner_metadata(tmp_path: Path) -> None:
    client = FakeHttpClient()
    trace_dir = tmp_path / "traces" / "run-2"
    runner = LiveRunner(
        endpoint=build_endpoint(),
        api_key="secret-key",
        dialect=OpenAIChatDialectAdapter(),
        http_client=client,
        trace_dir=trace_dir,
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
