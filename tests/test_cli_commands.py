from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact

ROOT = Path(__file__).resolve().parents[1]
runner = CliRunner()


def test_validate_prompts_and_show_suite_commands() -> None:
    result = runner.invoke(app, ["validate-prompts", "--root", str(ROOT)])
    assert result.exit_code == 0
    assert "validated 10 candidate prompts" in result.stdout

    suite = runner.invoke(app, ["show-suite", "screening-v1", "--root", str(ROOT)])
    assert suite.exit_code == 0
    assert "screening-v1" in suite.stdout
    assert "p009" in suite.stdout


def test_show_run_and_show_profile_commands(tmp_path: Path) -> None:
    run_path = tmp_path / "sample-run.json"
    run_path.write_text(
        json.dumps(
            RunArtifact.model_validate(
                {
                    "run_id": "suspect-a.default-v1",
                    "suite_id": "default-v1",
                    "target_label": "suspect-a",
                    "claimed_model": "gpt-5.3",
                    "prompts": [
                        {
                            "prompt_id": "p001",
                            "raw_output": "sample output",
                            "usage": {
                                "input_tokens": 10,
                                "output_tokens": 5,
                                "total_tokens": 15,
                            },
                            "features": {"char_len": 12},
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
                    "suite_id": "default-v1",
                    "sample_count": 2,
                    "prompts": [
                        {
                            "prompt_id": "p001",
                            "weight": 0.8,
                            "features": {
                                "char_len": {
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
    assert "suspect-a.default-v1" in show_run.stdout
    assert "prompt_count: 1" in show_run.stdout

    show_profile = runner.invoke(app, ["show-profile", str(profile_path), "--json"])
    assert show_profile.exit_code == 0
    assert '"model_id": "gpt-5.3"' in show_profile.stdout
