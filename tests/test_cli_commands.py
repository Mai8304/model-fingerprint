from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.feature_pipeline import PromptExecutionResult

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_validate_prompts_validate_endpoints_and_show_suite_commands(tmp_path: Path) -> None:
    endpoint_dir = tmp_path / "endpoint-profiles"
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
  supports_json_object_response: true
  supports_temperature: true
  supports_top_p: true
  supports_output_token_cap: true
request_mapping:
  output_token_cap_field: max_tokens
  json_response_shape:
    type: json_object
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
  max_attempts: 3
  retryable_statuses: [408, 429, 500, 502, 503, 504]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate-prompts", "--root", str(ROOT)])
    assert result.exit_code == 0
    assert "validated 25 prompt definitions and 6 suites" in result.stdout

    endpoint_result = runner.invoke(app, ["validate-endpoints", "--root", str(tmp_path)])
    assert endpoint_result.exit_code == 0
    assert "validated 1 endpoint profiles" in endpoint_result.stdout

    suite = runner.invoke(app, ["show-suite", "quick-check-v1", "--root", str(ROOT)])
    assert suite.exit_code == 0
    assert "quick-check-v1" in suite.stdout
    assert "p009" in suite.stdout


def test_show_run_and_show_profile_commands_print_v2_coverage_fields(tmp_path: Path) -> None:
    run_path = tmp_path / "sample-run.json"
    run_path.write_text(
        json.dumps(
            RunArtifact.model_validate(
                {
                    "run_id": "suspect-a.fingerprint-suite-v1",
                    "suite_id": "fingerprint-suite-v1",
                    "target_label": "suspect-a",
                    "claimed_model": "gpt-5.3",
                    "endpoint_profile_id": "siliconflow-openai-chat",
                    "answer_coverage_ratio": 1.0,
                    "reasoning_coverage_ratio": 0.5,
                    "runtime_policy": {
                        "policy_id": "single_request_progress_runtime_v1",
                        "thinking_probe_status": "supported",
                        "execution_class": "thinking",
                        "no_data_checkpoints_seconds": [30, 60],
                        "progress_poll_interval_seconds": 10,
                        "total_deadline_seconds": 120,
                        "output_token_cap": 3000,
                    },
                    "capability_probe": {
                        "probe_mode": "minimal",
                        "probe_version": "v1",
                        "coverage_ratio": 0.75,
                        "capabilities": {
                            "thinking": {
                                "status": "supported",
                                "detail": "reasoning visible",
                                "evidence": {"field": "reasoning"},
                            }
                        },
                    },
                    "protocol_compatibility": {
                        "satisfied": False,
                        "required_capabilities": ["chat_completions", "visible_reasoning"],
                        "issues": ["reasoning coverage is below the profile expectation"],
                    },
                    "prompts": [
                        {
                            "prompt_id": "p001",
                            "status": "completed",
                            "raw_output": "sample output",
                            "usage": {
                                "input_tokens": 10,
                                "output_tokens": 5,
                                "reasoning_tokens": 0,
                                "total_tokens": 15,
                            },
                            "attempts": [
                                {
                                    "request_attempt_index": 1,
                                    "read_timeout_seconds": 30,
                                    "output_token_cap": 3000,
                                    "status": "completed",
                                    "latency_ms": 1000,
                                    "finish_reason": "stop",
                                    "answer_text_present": True,
                                    "reasoning_visible": False,
                                    "bytes_received": 192,
                                    "first_byte_latency_ms": 400,
                                    "last_progress_latency_ms": 900,
                                    "completed": True,
                                }
                            ],
                            "features": {"answer.char_len": 12},
                        }
                    ],
                }
            ).model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    profile_path = tmp_path / "sample-profile.json"
    profile_path.write_text(
        json.dumps(
            ProfileArtifact.model_validate(
                {
                    "model_id": "gpt-5.3",
                    "suite_id": "fingerprint-suite-v1",
                    "sample_count": 2,
                    "answer_coverage_ratio": 1.0,
                    "reasoning_coverage_ratio": 0.5,
                    "capability_profile": {
                        "coverage_ratio": 0.75,
                        "capabilities": {
                            "thinking": {
                                "distribution": {
                                    "supported": 1.0,
                                }
                            }
                        },
                    },
                    "prompts": [
                        {
                            "prompt_id": "p001",
                            "weight": 0.8,
                            "answer_coverage_ratio": 1.0,
                            "reasoning_coverage_ratio": 0.5,
                            "expected_reasoning_visible": 0.5,
                            "features": {
                                "answer.char_len": {
                                    "kind": "numeric",
                                    "median": 42.0,
                                    "mad": 2.0,
                                }
                            },
                        }
                    ],
                }
            ).model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    show_run = runner.invoke(app, ["show-run", str(run_path)])
    assert show_run.exit_code == 0
    assert "answer_coverage_ratio: 1.0000" in show_run.stdout
    assert "reasoning_coverage_ratio: 0.5000" in show_run.stdout
    assert "capability_coverage_ratio: 0.7500" in show_run.stdout
    assert "protocol_status: incompatible_protocol" in show_run.stdout
    assert "runtime_execution_class: thinking" in show_run.stdout
    assert "runtime_no_data_checkpoints: 30,60" in show_run.stdout
    assert "runtime_progress_poll_interval_seconds: 10" in show_run.stdout
    assert "runtime_total_deadline_seconds: 120" in show_run.stdout
    assert "runtime_output_token_cap: 3000" in show_run.stdout

    show_run_json = runner.invoke(app, ["show-run", str(run_path), "--json"])
    assert show_run_json.exit_code == 0
    show_run_payload = RunArtifact.model_validate_json(show_run_json.stdout)
    assert show_run_payload.runtime_policy is not None
    assert show_run_payload.runtime_policy.output_token_cap == 3000
    assert show_run_payload.prompts[0].attempts[0].read_timeout_seconds == 30

    show_profile = runner.invoke(app, ["show-profile", str(profile_path)])
    assert show_profile.exit_code == 0
    assert "reasoning_coverage_ratio: 0.5000" in show_profile.stdout
    assert "capability_coverage_ratio: 0.7500" in show_profile.stdout
    assert "prompt_weights: p001=0.8000" in show_profile.stdout


@pytest.mark.usefixtures("monkeypatch")
def test_run_suite_live_mode_resolves_runtime_policy_and_serializes_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    endpoint_dir = tmp_path / "endpoint-profiles"
    endpoint_dir.mkdir(parents=True)
    (endpoint_dir / "openrouter-glm-5.yaml").write_text(
        """
id: openrouter-glm-5
dialect: openai_chat_v1
base_url: https://openrouter.ai/api/v1
model: z-ai/glm-5
auth:
  kind: bearer_env
  env_var: MODEL_FINGERPRINT_API_KEY
capabilities:
  exposes_reasoning_text: true
  supports_json_object_response: true
  supports_temperature: true
  supports_top_p: true
  supports_output_token_cap: true
request_mapping:
  output_token_cap_field: max_tokens
  json_response_shape:
    type: json_object
response_mapping:
  answer_text_path: choices.0.message.content
  reasoning_text_path: choices.0.message.reasoning
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
  max_attempts: 2
  retryable_statuses: [408, 429, 500, 502, 503, 504]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "prompt-bank").symlink_to(ROOT / "prompt-bank")
    (tmp_path / "extractors").symlink_to(ROOT / "extractors")
    monkeypatch.setenv("MODEL_FINGERPRINT_API_KEY", "secret-key")

    captured: dict[str, object] = {}

    def fake_probe_capabilities(*, base_url: str, api_key: str, model: str):
        return {
            "probe_mode": "minimal",
            "probe_version": "v1",
            "coverage_ratio": 1.0,
            "results": {
                "thinking": {"status": "supported"},
                "tools": {"status": "supported"},
                "streaming": {"status": "supported"},
                "image": {"status": "unsupported"},
            },
        }

    class FakeLiveRunner:
        def __init__(
            self,
            *,
            endpoint,
            api_key: str,
            dialect,
            trace_dir,
            runtime_policy,
            http_client=None,
        ) -> None:
            captured["runtime_policy"] = runtime_policy
            self.endpoint = endpoint
            self.trace_dir = trace_dir
            self.runtime_policy = runtime_policy

        def execute(self, prompt) -> PromptExecutionResult:
            payloads = {
                "p001": "Use CRUD first. Event sourcing adds overhead.",
                "p003": '{"answer":"yes","confidence":"high"}',
                "p005": '@@ -1 +1 @@\n-print("old")\n+print("new")',
                "p007": (
                    '{"requested_fields":["name","role"],"extracted":{"name":"Alice","role":"admin"},'
                    '"evidence":{"name":["e1"],"role":["e1"]},"hallucinated":[]}'
                ),
                "p009": (
                    '{"expected_needles":["alpha","beta","gamma"],'
                    '"found_needles":["alpha","beta","gamma"]}'
                ),
            }
            return PromptExecutionResult(
                prompt=prompt,
                raw_output=payloads[prompt.id],
                usage={
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "reasoning_tokens": 0,
                    "total_tokens": 15,
                },
            )

    monkeypatch.setattr("modelfingerprint.cli.probe_capabilities", fake_probe_capabilities)
    monkeypatch.setattr("modelfingerprint.cli.LiveRunner", FakeLiveRunner)

    result = runner.invoke(
        app,
        [
            "run-suite",
            "quick-check-v1",
            "--root",
            str(tmp_path),
            "--target-label",
            "live-suspect",
            "--endpoint-profile",
            "openrouter-glm-5",
            "--run-date",
            "2026-03-10",
        ],
    )

    assert result.exit_code == 0
    output_path = tmp_path / "runs" / "2026-03-10" / "live-suspect.quick-check-v1.json"
    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))
    assert captured["runtime_policy"] is not None
    assert artifact.runtime_policy is not None
    assert artifact.runtime_policy.execution_class == "thinking"
    assert artifact.runtime_policy.output_token_cap == 3000
