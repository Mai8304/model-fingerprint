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
    assert '"content_similarity"' in compare.stdout
    assert '"capability_similarity"' in compare.stdout
    assert '"capability_coverage_ratio"' in compare.stdout
    assert '"protocol_status": "compatible"' in compare.stdout
    assert '"answer_coverage_ratio": 1.0' in compare.stdout
    assert '"verdict": "match"' in compare.stdout


def test_golden_flow_fixture_execution_to_v3_verdict(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")
    write_endpoint_profile(tmp_path)

    glm_payload = {
        "p021": response(
            (
                '结果如下：\n```json\n'
                '{"result":{"owner":"Alice Wong","role":"Primary DBA","region":null,'
                '"change_window":"2026-03-21 02:00 UTC"},'
                '"evidence_map":{"owner":["e3"],"role":["e2"],'
                '"region":[],"change_window":["e5"]},"unknown_fields":{"region":"missing"},"violations":[]}\n```'
            ),
            "1. prefer approved facts\n2. keep region unknown",
            14,
        ),
        "p023": response(
            (
                '{"task_result":{"q1":{"status":"answer","value":"yes"},'
                '"q2":{"status":"unknown","value":null},'
                '"q3":{"status":"answer","value":"retry failed background jobs"},'
                '"q4":{"status":"conflict_unresolved","value":null}},'
                '"evidence":{"q1":["e1"],"q2":["e5"],"q3":["e1"],"q4":["e3","e4"]},'
                '"unknowns":{"q2":"missing_actor","q4":"conflicting_notes"},"violations":[]}'
            ),
            "1. split answer vs unknown vs conflict",
            18,
        ),
        "p024": response(
            (
                '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
                '"ticket_b":{"status":"open","owner":"db","priority":"p2"},'
                '"worker_x":{"status":"suspended","owner":"ml","priority":"p3"}},'
                '"evidence":{"derivation_codes":{"ticket_a":"r5","ticket_b":"r6","worker_x":"r10"},'
                '"defaults_used":["ticket_b.priority"]},"unknowns":{},"violations":[]}'
            ),
            "1. apply rules in order\n2. preserve owner on suspend",
            16,
        ),
    }
    other_payload = {
        "p021": response(
            (
                '{"task_result":{"owner":"Kevin Lin","role":"Primary DBA","region":"APAC",'
                '"change_window":"Sunday"},"evidence":{"owner":["e1"],"role":["e2"],"region":["e4"],'
                '"change_window":["e1"]},"unknowns":{},"violations":[]}'
            ),
            "1. trust the draft sheet",
            10,
        ),
        "p023": response(
            (
                '{"task_result":{"q1":{"status":"answer","value":"yes"},'
                '"q2":{"status":"answer","value":"Priya"},'
                '"q3":{"status":"answer","value":"retry failed background jobs"},'
                '"q4":{"status":"unknown","value":null}},'
                '"evidence":{"q1":["e1"],"q2":["e5"],"q3":["e1"],"q4":["e4"]},"unknowns":{"q4":"missing"},"violations":[]}'
            ),
            "1. answer the actor from context",
            11,
        ),
        "p024": response(
            (
                '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
                '"ticket_b":{"status":"open","owner":"db","priority":"p2"},'
                '"worker_x":{"status":"open","owner":"ops","priority":"p2"}},'
                '"evidence":{"derivation_codes":{"ticket_a":"r5","ticket_b":"r6","worker_x":"r8"},'
                '"defaults_used":["ticket_b.priority","worker_x.priority"]},"unknowns":{},"violations":[]}'
            ),
            "1. stop at suspend",
            9,
        ),
    }
    write_responses(tmp_path / "glm-v3-a1.json", glm_payload)
    write_responses(tmp_path / "glm-v3-a2.json", glm_payload)
    write_responses(tmp_path / "other-v3-a1.json", other_payload)
    write_responses(tmp_path / "other-v3-a2.json", other_payload)
    write_responses(tmp_path / "suspect-v3.json", glm_payload)

    assert runner.invoke(app, ["validate-prompts", "--root", str(tmp_path)]).exit_code == 0

    for target, claimed, fixture in [
        ("glm-v3-a1", "glm-5", "glm-v3-a1.json"),
        ("glm-v3-a2", "glm-5", "glm-v3-a2.json"),
        ("other-v3-a1", "other-model", "other-v3-a1.json"),
        ("other-v3-a2", "other-model", "other-v3-a2.json"),
        ("suspect-v3", "glm-5", "suspect-v3.json"),
    ]:
        result = runner.invoke(
            app,
            [
                "run-suite",
                "quick-check-v3",
                "--root",
                str(tmp_path),
                "--target-label",
                target,
                "--claimed-model",
                claimed,
                "--fixture-responses",
                str(tmp_path / fixture),
                "--run-date",
                "2026-03-10",
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
            "glm-5",
            "--run",
            str(tmp_path / "runs/2026-03-10/glm-v3-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-10/glm-v3-a2.quick-check-v3.json"),
        ],
    ).exit_code == 0
    assert runner.invoke(
        app,
        [
            "build-profile",
            "--root",
            str(tmp_path),
            "--model-id",
            "other-model",
            "--run",
            str(tmp_path / "runs/2026-03-10/other-v3-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-10/other-v3-a2.quick-check-v3.json"),
        ],
    ).exit_code == 0
    assert runner.invoke(
        app,
        [
            "calibrate",
            "--root",
            str(tmp_path),
            "--profile",
            str(tmp_path / "profiles/quick-check-v3/glm-5.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v3/other-model.json"),
            "--run",
            str(tmp_path / "runs/2026-03-10/glm-v3-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-10/glm-v3-a2.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-10/other-v3-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-10/other-v3-a2.quick-check-v3.json"),
        ],
    ).exit_code == 0

    compare = runner.invoke(
        app,
        [
            "compare",
            "--run",
            str(tmp_path / "runs/2026-03-10/suspect-v3.quick-check-v3.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v3/glm-5.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v3/other-model.json"),
            "--calibration",
            str(tmp_path / "calibration/quick-check-v3.json"),
            "--json",
        ],
    )

    assert compare.exit_code == 0
    assert '"top1_model": "glm-5"' in compare.stdout
    assert '"content_similarity"' in compare.stdout
    assert '"capability_similarity"' in compare.stdout
    assert '"answer_coverage_ratio": 1.0' in compare.stdout
