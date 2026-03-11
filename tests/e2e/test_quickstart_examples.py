from __future__ import annotations

import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = ROOT / "examples" / "quickstart" / "quick-check-v3"
runner = CliRunner()


def test_quickstart_examples_support_the_documented_v3_offline_flow(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")
    shutil.copytree(ROOT / "endpoint-profiles", tmp_path / "endpoint-profiles")

    expected_fixtures = {
        "glm-5-a1": EXAMPLES_DIR / "glm-5-a1.json",
        "glm-5-a2": EXAMPLES_DIR / "glm-5-a2.json",
        "claude-ops-4.6-a1": EXAMPLES_DIR / "claude-ops-4.6-a1.json",
        "claude-ops-4.6-a2": EXAMPLES_DIR / "claude-ops-4.6-a2.json",
        "suspect": EXAMPLES_DIR / "suspect.json",
    }
    for fixture_path in expected_fixtures.values():
        assert fixture_path.exists(), fixture_path

    assert runner.invoke(app, ["validate-prompts", "--root", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["validate-endpoints", "--root", str(tmp_path)]).exit_code == 0

    for target, claimed_model, fixture_name in [
        ("glm-5-a1", "glm-5", "glm-5-a1"),
        ("glm-5-a2", "glm-5", "glm-5-a2"),
        ("claude-ops-4.6-a1", "claude-ops-4.6", "claude-ops-4.6-a1"),
        ("claude-ops-4.6-a2", "claude-ops-4.6", "claude-ops-4.6-a2"),
        ("suspect-v3", "glm-5", "suspect"),
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
                claimed_model,
                "--fixture-responses",
                str(expected_fixtures[fixture_name]),
                "--run-date",
                "2026-03-11",
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
            str(tmp_path / "runs/2026-03-11/glm-5-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-11/glm-5-a2.quick-check-v3.json"),
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
            str(tmp_path / "runs/2026-03-11/claude-ops-4.6-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-11/claude-ops-4.6-a2.quick-check-v3.json"),
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
            str(tmp_path / "profiles/quick-check-v3/claude-ops-4.6.json"),
            "--run",
            str(tmp_path / "runs/2026-03-11/glm-5-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-11/glm-5-a2.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-11/claude-ops-4.6-a1.quick-check-v3.json"),
            "--run",
            str(tmp_path / "runs/2026-03-11/claude-ops-4.6-a2.quick-check-v3.json"),
        ],
    ).exit_code == 0

    compare = runner.invoke(
        app,
        [
            "compare",
            "--run",
            str(tmp_path / "runs/2026-03-11/suspect-v3.quick-check-v3.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v3/glm-5.json"),
            "--profile",
            str(tmp_path / "profiles/quick-check-v3/claude-ops-4.6.json"),
            "--calibration",
            str(tmp_path / "calibration/quick-check-v3.json"),
            "--artifact-json",
        ],
    )

    assert compare.exit_code == 0
    assert '"schema_version": "comparison.v1"' in compare.stdout
    assert '"top1_model": "glm-5"' in compare.stdout
    assert '"protocol_status": "compatible"' in compare.stdout
    assert '"verdict": "match"' in compare.stdout
