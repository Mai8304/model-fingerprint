from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact

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
                        "policy_id": "thinking_aware_runtime_v1",
                        "thinking_probe_status": "supported",
                        "execution_class": "thinking",
                        "round_windows_seconds": [30, 30],
                        "max_rounds": 2,
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
                                    "round_index": 1,
                                    "window_index": 1,
                                    "http_attempt_index": 1,
                                    "read_timeout_seconds": 30,
                                    "output_token_cap": 3000,
                                    "status": "completed",
                                    "latency_ms": 1000,
                                    "finish_reason": "stop",
                                    "answer_text_present": True,
                                    "reasoning_visible": False,
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
