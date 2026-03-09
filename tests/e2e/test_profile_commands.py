from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def test_build_profile_calibrate_and_compare_commands(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")

    gpt_profile = runner.invoke(
        app,
        [
            "build-profile",
            "--root",
            str(tmp_path),
            "--model-id",
            "gpt-5.3",
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/gpt_run1.json"),
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/gpt_run2.json"),
        ],
    )
    assert gpt_profile.exit_code == 0

    claude_profile = runner.invoke(
        app,
        [
            "build-profile",
            "--root",
            str(tmp_path),
            "--model-id",
            "claude-ops-4.6",
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/claude_run1.json"),
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/claude_run2.json"),
        ],
    )
    assert claude_profile.exit_code == 0

    calibrate = runner.invoke(
        app,
        [
            "calibrate",
            "--root",
            str(tmp_path),
            "--profile",
            str(tmp_path / "profiles/default-v1/gpt-5.3.json"),
            "--profile",
            str(tmp_path / "profiles/default-v1/claude-ops-4.6.json"),
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/gpt_run1.json"),
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/gpt_run2.json"),
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/claude_run1.json"),
            "--run",
            str(ROOT / "tests/fixtures/calibration_runs/claude_run2.json"),
        ],
    )
    assert calibrate.exit_code == 0

    suspect_path = tmp_path / "suspect-run.json"
    suspect_path.write_text(
        json.dumps(
            {
                "run_id": "suspect-a.default-v1",
                "suite_id": "default-v1",
                "target_label": "suspect-a",
                "claimed_model": "gpt-5.3",
                "prompts": [
                    {
                        "prompt_id": "p001",
                        "raw_output": "suspect sample",
                        "usage": {
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "total_tokens": 15,
                        },
                        "features": {
                            "char_len": 41,
                            "uses_numbered_list": True,
                            "abstraction_level": "concrete",
                        },
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    compare = runner.invoke(
        app,
        [
            "compare",
            "--run",
            str(suspect_path),
            "--profile",
            str(tmp_path / "profiles/default-v1/gpt-5.3.json"),
            "--profile",
            str(tmp_path / "profiles/default-v1/claude-ops-4.6.json"),
            "--calibration",
            str(tmp_path / "calibration/default-v1.json"),
            "--json",
        ],
    )
    assert compare.exit_code == 0
    assert '"top1_model": "gpt-5.3"' in compare.stdout
    assert '"verdict": "match"' in compare.stdout
