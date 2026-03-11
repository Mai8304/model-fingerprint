from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.run import RunArtifact

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def write_run(
    path: Path,
    *,
    run_id: str,
    target_label: str,
    claimed_model: str,
    p021_char_len: int,
    p021_step_count: int,
    p023_char_len: int,
) -> None:
    artifact = RunArtifact.model_validate(
        {
            "run_id": run_id,
            "suite_id": "fingerprint-suite-v3",
            "target_label": target_label,
            "claimed_model": claimed_model,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 1.0,
            "protocol_compatibility": {
                "satisfied": True,
                "required_capabilities": ["chat_completions", "visible_reasoning"],
                "issues": [],
            },
            "prompts": [
                {
                    "prompt_id": "p021",
                    "status": "completed",
                    "raw_output": "sample-p021",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "reasoning_tokens": 12,
                        "total_tokens": 15,
                    },
                    "features": {
                        "answer.char_len": p021_char_len,
                        "reasoning.step_count": p021_step_count,
                        "transport.reasoning_visible": True,
                        "surface.had_markdown_fence": False,
                    },
                },
                {
                    "prompt_id": "p023",
                    "status": "completed",
                    "raw_output": "sample-p023",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "reasoning_tokens": 0,
                        "total_tokens": 15,
                    },
                    "features": {
                        "answer.char_len": p023_char_len,
                        "transport.reasoning_visible": False,
                        "surface.had_markdown_fence": False,
                    },
                },
            ],
        }
    )
    path.write_text(
        json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def test_build_profile_calibrate_and_compare_commands_emit_v3_fields(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")

    write_run(
        tmp_path / "gpt-run1.json",
        run_id="gpt-1",
        target_label="gpt-5.3",
        claimed_model="gpt-5.3",
        p021_char_len=40,
        p021_step_count=2,
        p023_char_len=20,
    )
    write_run(
        tmp_path / "gpt-run2.json",
        run_id="gpt-2",
        target_label="gpt-5.3",
        claimed_model="gpt-5.3",
        p021_char_len=42,
        p021_step_count=2,
        p023_char_len=22,
    )
    write_run(
        tmp_path / "claude-run1.json",
        run_id="claude-1",
        target_label="claude-ops-4.6",
        claimed_model="claude-ops-4.6",
        p021_char_len=90,
        p021_step_count=5,
        p023_char_len=200,
    )
    write_run(
        tmp_path / "claude-run2.json",
        run_id="claude-2",
        target_label="claude-ops-4.6",
        claimed_model="claude-ops-4.6",
        p021_char_len=88,
        p021_step_count=4,
        p023_char_len=198,
    )

    gpt_profile = runner.invoke(
        app,
        [
            "build-profile",
            "--root",
            str(tmp_path),
            "--model-id",
            "gpt-5.3",
            "--run",
            str(tmp_path / "gpt-run1.json"),
            "--run",
            str(tmp_path / "gpt-run2.json"),
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
            str(tmp_path / "claude-run1.json"),
            "--run",
            str(tmp_path / "claude-run2.json"),
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
            str(tmp_path / "profiles/fingerprint-suite-v3/gpt-5.3.json"),
            "--profile",
            str(tmp_path / "profiles/fingerprint-suite-v3/claude-ops-4.6.json"),
            "--run",
            str(tmp_path / "gpt-run1.json"),
            "--run",
            str(tmp_path / "gpt-run2.json"),
            "--run",
            str(tmp_path / "claude-run1.json"),
            "--run",
            str(tmp_path / "claude-run2.json"),
        ],
    )
    assert calibrate.exit_code == 0

    write_run(
        tmp_path / "suspect-run.json",
        run_id="suspect-a",
        target_label="suspect-a",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p023_char_len=199,
    )

    compare = runner.invoke(
        app,
        [
            "compare",
            "--run",
            str(tmp_path / "suspect-run.json"),
            "--profile",
            str(tmp_path / "profiles/fingerprint-suite-v3/gpt-5.3.json"),
            "--profile",
            str(tmp_path / "profiles/fingerprint-suite-v3/claude-ops-4.6.json"),
            "--calibration",
            str(tmp_path / "calibration/fingerprint-suite-v3.json"),
            "--json",
        ],
    )
    assert compare.exit_code == 0
    assert '"top1_model": "gpt-5.3"' in compare.stdout
    assert '"content_similarity"' in compare.stdout
    assert '"capability_similarity"' in compare.stdout
    assert '"capability_coverage_ratio"' in compare.stdout
    assert '"answer_similarity"' in compare.stdout
    assert '"reasoning_similarity"' in compare.stdout
    assert '"answer_coverage_ratio": 1.0' in compare.stdout
    assert '"reasoning_coverage_ratio": 1.0' in compare.stdout
    assert '"protocol_status": "compatible"' in compare.stdout

    compare_artifact = runner.invoke(
        app,
        [
            "compare",
            "--run",
            str(tmp_path / "suspect-run.json"),
            "--profile",
            str(tmp_path / "profiles/fingerprint-suite-v3/gpt-5.3.json"),
            "--profile",
            str(tmp_path / "profiles/fingerprint-suite-v3/claude-ops-4.6.json"),
            "--calibration",
            str(tmp_path / "calibration/fingerprint-suite-v3.json"),
            "--artifact-json",
        ],
    )
    assert compare_artifact.exit_code == 0
    assert '"schema_version": "comparison.v1"' in compare_artifact.stdout
    assert '"summary"' in compare_artifact.stdout
    assert '"candidates"' in compare_artifact.stdout
    assert '"prompt_breakdown"' in compare_artifact.stdout
    assert '"capability_breakdown"' in compare_artifact.stdout
