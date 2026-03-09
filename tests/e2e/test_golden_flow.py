from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app

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


def write_responses(path: Path, payload: dict[str, dict[str, object]]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def response(content: str, reasoning_content: str, reasoning_tokens: int) -> dict[str, object]:
    return {
        "content": content,
        "reasoning_content": reasoning_content,
        "input_tokens": 10,
        "output_tokens": 5,
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": 15 + reasoning_tokens,
        "finish_reason": "stop",
    }


def test_golden_flow_fixture_execution_to_v2_verdict(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")
    write_endpoint_profile(tmp_path)

    gpt_payload = {
        "p001": response(
            "Use CRUD first. Event sourcing adds overhead.",
            "1. inspect the request\n2. answer briefly",
            8,
        ),
        "p003": response(
            '{"answer":"yes","confidence":"high"}',
            "1. inspect the schema\n2. return strict json",
            12,
        ),
        "p005": response(
            '@@ -1 +1 @@\n-print("old")\n+print("new")',
            "1. isolate the line\n2. emit the diff",
            6,
        ),
        "p007": response(
            (
                '{"requested_fields":["name","role"],"extracted":{"name":"Alice","role":"admin"},'
                '"evidence":{"name":["e1"],"role":["e1"]},"hallucinated":[]}'
            ),
            "1. inspect evidence ids\n2. fill requested fields only",
            10,
        ),
        "p009": response(
            '{"expected_needles":["alpha","beta","gamma"],"found_needles":["alpha","beta","gamma"]}',
            "1. scan the entities\n2. preserve order",
            9,
        ),
    }
    claude_payload = {
        "p001": response(
            "Maybe consider event sourcing. It depends.",
            "1. maybe inspect the context\n2. however reconsider the answer",
            14,
        ),
        "p003": response(
            '```json\n{"confidence":"high","answer":"yes"}\n```',
            "1. parse the question\n2. answer with fenced json",
            13,
        ),
        "p005": response(
            '@@ -1,2 +1,2 @@\n-alpha\n-beta\n+beta\n+alpha',
            "1. reorder the lines\n2. emit the patch",
            11,
        ),
        "p007": response(
            (
                '{"requested_fields":["name","role"],"extracted":{"name":"Alice","city":"Paris"},'
                '"evidence":["name"],"hallucinated":["city"]}'
            ),
            "1. inspect some evidence\n2. infer the rest",
            12,
        ),
        "p009": response(
            '{"expected_needles":["alpha","beta","gamma"],"found_needles":["gamma","delta","alpha"]}',
            "1. scan the text\n2. maybe answer from memory",
            10,
        ),
    }
    write_responses(tmp_path / "gpt-a1.json", gpt_payload)
    write_responses(tmp_path / "gpt-a2.json", gpt_payload)
    write_responses(tmp_path / "claude-a1.json", claude_payload)
    write_responses(tmp_path / "claude-a2.json", claude_payload)
    write_responses(tmp_path / "suspect.json", gpt_payload)

    assert runner.invoke(app, ["validate-prompts", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["validate-endpoints", "--root", str(tmp_path)]).exit_code == 0

    for target, claimed, fixture in [
        ("gpt-a1", "gpt-5.3", "gpt-a1.json"),
        ("gpt-a2", "gpt-5.3", "gpt-a2.json"),
        ("claude-a1", "claude-ops-4.6", "claude-a1.json"),
        ("claude-a2", "claude-ops-4.6", "claude-a2.json"),
        ("suspect-a", "gpt-5.3", "suspect.json"),
    ]:
        result = runner.invoke(
            app,
            [
                "run-suite",
                "quick-check-v1",
                "--root",
                str(tmp_path),
                "--target-label",
                target,
                "--claimed-model",
                claimed,
                "--fixture-responses",
                str(tmp_path / fixture),
                "--run-date",
                "2026-03-09",
            ],
        )
        assert result.exit_code == 0

    assert runner.invoke(
        app,
        [
            "build-profile",
            "--root",
            str(tmp_path),
            "--model-id",
            "gpt-5.3",
            "--run",
            str(tmp_path / "runs/2026-03-09/gpt-a1.quick-check-v1.json"),
            "--run",
            str(tmp_path / "runs/2026-03-09/gpt-a2.quick-check-v1.json"),
        ],
    ).exit_code == 0
    assert runner.invoke(
        app,
        [
            "build-profile",
            "--root",
            str(tmp_path),
            "--model-id",
            "claude-ops-4.6",
            "--run",
            str(tmp_path / "runs/2026-03-09/claude-a1.quick-check-v1.json"),
            "--run",
            str(tmp_path / "runs/2026-03-09/claude-a2.quick-check-v1.json"),
        ],
    ).exit_code == 0
    assert runner.invoke(
        app,
        [
            "calibrate",
            "--root",
            str(tmp_path),
            "--profile",
            str(tmp_path / "profiles/quick-check-v1/gpt-5.3.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v1/claude-ops-4.6.json"),
            "--run",
            str(tmp_path / "runs/2026-03-09/gpt-a1.quick-check-v1.json"),
            "--run",
            str(tmp_path / "runs/2026-03-09/gpt-a2.quick-check-v1.json"),
            "--run",
            str(tmp_path / "runs/2026-03-09/claude-a1.quick-check-v1.json"),
            "--run",
            str(tmp_path / "runs/2026-03-09/claude-a2.quick-check-v1.json"),
        ],
    ).exit_code == 0

    compare = runner.invoke(
        app,
        [
            "compare",
            "--run",
            str(tmp_path / "runs/2026-03-09/suspect-a.quick-check-v1.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v1/gpt-5.3.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v1/claude-ops-4.6.json"),
            "--calibration",
            str(tmp_path / "calibration/quick-check-v1.json"),
            "--json",
        ],
    )

    assert compare.exit_code == 0
    assert '"top1_model": "gpt-5.3"' in compare.stdout
    assert '"protocol_status": "compatible"' in compare.stdout
    assert '"answer_coverage_ratio": 1.0' in compare.stdout
    assert '"verdict": "match"' in compare.stdout
