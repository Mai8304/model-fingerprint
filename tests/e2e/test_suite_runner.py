from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.run import RunArtifact

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def write_fixture_responses(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "p001": {
                    "content": "Use CRUD first. Event sourcing adds overhead.",
                    "reasoning_content": "1. evaluate scope\n2. answer briefly",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "reasoning_tokens": 8,
                    "total_tokens": 23,
                    "finish_reason": "stop",
                },
                "p003": {
                    "content": '{"answer":"yes","confidence":"high"}',
                    "reasoning_content": "1. inspect the schema\n2. return strict json",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "reasoning_tokens": 12,
                    "total_tokens": 27,
                    "finish_reason": "stop",
                },
                "p005": {
                    "content": '@@ -1 +1 @@\n-print("old")\n+print("new")',
                    "reasoning_content": "1. isolate the target line\n2. emit diff only",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "reasoning_tokens": 6,
                    "total_tokens": 21,
                    "finish_reason": "stop",
                },
                "p007": {
                    "content": (
                        '{"requested_fields":["name","role"],"extracted":{"name":"Alice","role":"admin"},'
                        '"evidence":{"name":["e1"],"role":["e1"]},"hallucinated":[]}'
                    ),
                    "reasoning_content": "1. inspect evidence ids\n2. fill requested fields only",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "reasoning_tokens": 10,
                    "total_tokens": 25,
                    "finish_reason": "stop",
                },
                "p009": {
                    "content": (
                        '{"expected_needles":["alpha","beta","gamma"],'
                        '"found_needles":["alpha","beta","gamma"]}'
                    ),
                    "reasoning_content": "1. scan the requested entities\n2. preserve order",
                    "input_tokens": 10,
                    "output_tokens": 5,
                    "reasoning_tokens": 9,
                    "total_tokens": 24,
                    "finish_reason": "stop",
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_run_suite_command_executes_fixture_mode_and_writes_v2_run(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")
    fixture_path = tmp_path / "responses.json"
    write_fixture_responses(fixture_path)

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
            "--fixture-responses",
            str(fixture_path),
            "--run-date",
            "2026-03-09",
        ],
    )

    assert result.exit_code == 0

    output_path = tmp_path / "runs" / "2026-03-09" / "suspect-a.quick-check-v1.json"
    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    assert artifact.suite_id == "quick-check-v1"
    assert artifact.prompt_count_total == 5
    assert artifact.prompt_count_completed == 5
    assert artifact.answer_coverage_ratio == 1.0
    assert artifact.reasoning_coverage_ratio == 1.0
    assert artifact.capability_probe is None
    assert artifact.protocol_compatibility is not None
    assert artifact.protocol_compatibility.satisfied is True
    assert all(prompt.completion is not None for prompt in artifact.prompts)


def write_v3_fixture_responses(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "p021": {
                    "content": (
                        '结果如下：\n```json\n'
                        '{"result":{"owner":"Alice Wong","role":"Primary DBA","region":null,'
                        '"change_window":"2026-03-21 02:00 UTC"},'
                        '"evidence_map":{"owner":["e3"],"role":["e2"],"region":[],"change_window":["e5"]},'
                        '"unknown_fields":{"region":"missing"},"violations":[]}\n```\n谢谢'
                    ),
                    "reasoning_content": "1. ignore draft facts\n2. keep region unknown",
                    "input_tokens": 20,
                    "output_tokens": 30,
                    "reasoning_tokens": 18,
                    "total_tokens": 68,
                    "finish_reason": "stop",
                },
                "p023": {
                    "content": (
                        '{"task_result":{"q1":{"status":"answer","value":"yes"},'
                        '"q2":{"status":"unknown","value":null},'
                        '"q3":{"status":"answer","value":"retry failed background jobs"},'
                        '"q4":{"status":"conflict_unresolved","value":null}},'
                        '"evidence":{"q1":["e1"],"q2":["e5"],"q3":["e1"],"q4":["e3","e4"]},'
                        '"unknowns":{"q2":"missing_actor","q4":"conflicting_notes"},"violations":[]}'
                    ),
                    "reasoning_content": (
                        "1. split answerable from unresolved\n2. keep q4 conflicted"
                    ),
                    "input_tokens": 24,
                    "output_tokens": 28,
                    "reasoning_tokens": 21,
                    "total_tokens": 73,
                    "finish_reason": "stop",
                },
                "p024": {
                    "content": (
                        'Final JSON: '
                        '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
                        '"ticket_b":{"status":"open","owner":"db","priority":"p2"},'
                        '"worker_x":{"status":"suspended","owner":"ml","priority":"p3"}},'
                        '"evidence":{"derivation_codes":{"ticket_a":"r5","ticket_b":"r6","worker_x":"r10"},'
                        '"defaults_used":["ticket_b.priority"]},"unknowns":{},"violations":[]}'
                    ),
                    "reasoning_content": (
                        "1. apply close/reopen rules\n2. preserve owner on suspend"
                    ),
                    "input_tokens": 30,
                    "output_tokens": 32,
                    "reasoning_tokens": 25,
                    "total_tokens": 87,
                    "finish_reason": "stop",
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_run_suite_command_executes_fixture_mode_and_writes_v3_run(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")
    fixture_path = tmp_path / "v3-responses.json"
    write_v3_fixture_responses(fixture_path)

    result = runner.invoke(
        app,
        [
            "run-suite",
            "quick-check-v3",
            "--root",
            str(tmp_path),
            "--target-label",
            "suspect-v3",
            "--claimed-model",
            "glm-5",
            "--fixture-responses",
            str(fixture_path),
            "--run-date",
            "2026-03-10",
        ],
    )

    assert result.exit_code == 0

    output_path = tmp_path / "runs" / "2026-03-10" / "suspect-v3.quick-check-v3.json"
    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    assert artifact.suite_id == "quick-check-v3"
    assert artifact.prompt_count_total == 3
    assert artifact.prompt_count_completed == 3
    assert artifact.prompt_count_scoreable == 3
    assert artifact.answer_coverage_ratio == 1.0
    assert artifact.reasoning_coverage_ratio == 1.0
    assert artifact.capability_probe is None
    assert artifact.protocol_compatibility is not None
    assert artifact.protocol_compatibility.satisfied is True
    assert all(prompt.canonical_output is not None for prompt in artifact.prompts)
