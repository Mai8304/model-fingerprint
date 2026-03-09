from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.run import RunArtifact

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def write_endpoint_profile(root: Path) -> None:
    endpoint_dir = root / "endpoint-profiles"
    endpoint_dir.mkdir(parents=True)
    (endpoint_dir / "siliconflow-openai-chat.yaml").write_text(
        """
id: siliconflow-openai-chat
dialect: openai_chat_v1
base_url: https://api.siliconflow.cn/v1
model: Pro/zai-org/GLM-5
auth:
  kind: bearer_env
  env_var: MODEL_FINGERPRINT_API_KEY
capabilities:
  exposes_reasoning_text: true
  supports_json_object_response: false
  supports_temperature: true
  supports_top_p: true
  supports_output_token_cap: true
request_mapping:
  output_token_cap_field: max_tokens
response_mapping:
  answer_text_path: choices.0.message.content
  reasoning_text_path: choices.0.message.reasoning_content
  finish_reason_path: choices.0.finish_reason
  usage_paths:
    prompt_tokens: usage.prompt_tokens
    output_tokens: usage.completion_tokens
    total_tokens: usage.total_tokens
    reasoning_tokens: usage.completion_tokens_details.reasoning_tokens
timeout_policy:
  connect_seconds: 10
  read_seconds: 120
retry_policy:
  max_attempts: 1
  retryable_statuses: [408, 429, 500, 502, 503, 504]
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_run_suite_command_uses_endpoint_profiles_and_preserves_failures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")
    write_endpoint_profile(tmp_path)
    monkeypatch.setenv("MODEL_FINGERPRINT_API_KEY", "secret-key")

    def fake_send(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        user_message = request.body["messages"][-1]["content"]
        if "event sourcing" in user_message:
            payload = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "Use CRUD first. Event sourcing adds overhead.",
                            "reasoning_content": "1. inspect the request\n2. answer briefly",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 21,
                    "completion_tokens_details": {"reasoning_tokens": 6},
                },
            }
        else:
            payload = {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '@@ -1 +1 @@\n-print("old")\n+print("new")',
                            "reasoning_content": "1. isolate the target line\n2. emit the diff",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 5,
                    "total_tokens": 22,
                    "completion_tokens_details": {"reasoning_tokens": 7},
                },
            }
        return payload, 3210

    monkeypatch.setattr(
        "modelfingerprint.transports.http_client.StandardHttpClient.send",
        fake_send,
    )
    monkeypatch.setattr(
        "modelfingerprint.cli.probe_capabilities",
        lambda **_: {
            "base_url": "https://api.siliconflow.cn/v1",
            "model": "Pro/zai-org/GLM-5",
            "probe_mode": "minimal",
            "probe_version": "v1",
            "coverage_ratio": 0.75,
            "results": {
                "thinking": {
                    "capability": "thinking",
                    "status": "supported",
                    "detail": "reasoning field is populated",
                    "evidence": {"field": "reasoning"},
                    "http_status": 200,
                    "latency_ms": 1000,
                },
                "tools": {
                    "capability": "tools",
                    "status": "insufficient_evidence",
                    "detail": "429",
                    "evidence": {"http_status": 429},
                    "http_status": 429,
                    "latency_ms": 800,
                },
                "streaming": {
                    "capability": "streaming",
                    "status": "supported",
                    "detail": "sse",
                    "evidence": {"content_type": "text/event-stream"},
                    "http_status": 200,
                    "latency_ms": 700,
                },
                "image": {
                    "capability": "image",
                    "status": "unsupported",
                    "detail": "404",
                    "evidence": {"http_status": 404},
                    "http_status": 404,
                    "latency_ms": 600,
                },
            },
        },
    )

    result = runner.invoke(
        app,
        [
            "run-suite",
            "quick-check-v1",
            "--root",
            str(tmp_path),
            "--target-label",
            "suspect-a",
            "--claimed-model",
            "gpt-5.3",
            "--endpoint-profile",
            "siliconflow-openai-chat",
            "--run-date",
            "2026-03-09",
        ],
    )

    assert result.exit_code == 0

    output_path = tmp_path / "runs" / "2026-03-09" / "suspect-a.quick-check-v1.json"
    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    assert artifact.endpoint_profile_id == "siliconflow-openai-chat"
    assert artifact.capability_probe is not None
    assert artifact.capability_probe.probe_mode == "minimal"
    assert artifact.capability_probe.capabilities["thinking"].status == "supported"
    assert artifact.trace_dir is not None
    assert artifact.protocol_compatibility is not None
    assert artifact.protocol_compatibility.satisfied is False
    prompt_statuses = {prompt.prompt_id: prompt.status for prompt in artifact.prompts}
    assert prompt_statuses["p003"] == "unsupported_capability"
    assert prompt_statuses["p007"] == "unsupported_capability"
    assert prompt_statuses["p009"] == "unsupported_capability"
    assert (
        tmp_path / "traces" / "2026-03-09" / "suspect-a.quick-check-v1" / "p001.request.json"
    ).exists()
