from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def write_responses(path: Path, payload: dict[str, dict[str, object]]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def response(content: str) -> dict[str, object]:
    return {
        "content": content,
        "input_tokens": 10,
        "output_tokens": 5,
        "total_tokens": 15,
    }


def test_golden_flow_screening_to_verdict(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")

    gpt_payload = {
        "p001": response("Use CRUD first. Event sourcing adds overhead."),
        "p003": response('{"answer":"yes","confidence":"high"}'),
        "p005": response('@@ -1 +1 @@\n-print("old")\n+print("new")'),
        "p007": response(
            '{"requested_fields":["name","role"],"extracted":{"name":"Alice","role":"admin"},'
            '"evidence":["name","role"],"hallucinated":[]}'
        ),
        "p009": response(
            '{"expected_needles":["alpha","beta","gamma"],"found_needles":["alpha","beta","gamma"]}'
        ),
    }
    claude_payload = {
        "p001": response("Maybe consider event sourcing. It depends."),
        "p003": response('Result:\n{"confidence":"high","answer":"yes"}'),
        "p005": response('@@ -1,2 +1,2 @@\n-alpha\n-beta\n+beta\n+alpha'),
        "p007": response(
            '{"requested_fields":["name","role"],"extracted":{"name":"Alice","city":"Paris"},'
            '"evidence":["name"],"hallucinated":["city"]}'
        ),
        "p009": response(
            '{"expected_needles":["alpha","beta","gamma"],"found_needles":["gamma","delta","alpha"]}'
        ),
    }
    write_responses(tmp_path / "gpt-a1.json", gpt_payload)
    write_responses(tmp_path / "gpt-a2.json", gpt_payload)
    write_responses(tmp_path / "claude-a1.json", claude_payload)
    write_responses(tmp_path / "claude-a2.json", claude_payload)
    write_responses(tmp_path / "suspect.json", gpt_payload)

    assert runner.invoke(app, ["validate-prompts", "--root", str(tmp_path)]).exit_code == 0

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
    assert '"verdict": "match"' in compare.stdout
