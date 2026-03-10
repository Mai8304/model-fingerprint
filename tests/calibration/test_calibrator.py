from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.calibrator import Calibrator
from modelfingerprint.services.profile_builder import build_profile
from modelfingerprint.settings import RepositoryPaths


def build_run(
    *,
    run_id: str,
    model_id: str,
    p001_char_len: int,
    p001_step_count: int,
    p002_char_len: int,
) -> RunArtifact:
    return RunArtifact.model_validate(
        {
            "run_id": run_id,
            "suite_id": "fingerprint-suite-v3",
            "target_label": model_id,
            "claimed_model": model_id,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 1.0,
            "protocol_compatibility": {
                "satisfied": True,
                "required_capabilities": ["chat_completions", "visible_reasoning"],
                "issues": [],
            },
            "prompts": [
                {
                    "prompt_id": "p001",
                    "status": "completed",
                    "raw_output": "sample-p001",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "reasoning_tokens": 12,
                        "total_tokens": 15,
                    },
                    "features": {
                        "answer.char_len": p001_char_len,
                        "reasoning.step_count": p001_step_count,
                        "transport.reasoning_visible": True,
                        "surface.had_markdown_fence": False,
                    },
                },
                {
                    "prompt_id": "p002",
                    "status": "completed",
                    "raw_output": "sample-p002",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "reasoning_tokens": 4,
                        "total_tokens": 15,
                    },
                    "features": {
                        "answer.char_len": p002_char_len,
                        "transport.reasoning_visible": True,
                        "surface.had_markdown_fence": False,
                    },
                },
            ],
        }
    )


def test_calibrator_builds_similarity_and_coverage_thresholds(tmp_path: Path) -> None:
    gpt_runs = [
        build_run(
            run_id="gpt-1",
            model_id="gpt-5.3",
            p001_char_len=40,
            p001_step_count=2,
            p002_char_len=20,
        ),
        build_run(
            run_id="gpt-2",
            model_id="gpt-5.3",
            p001_char_len=42,
            p001_step_count=2,
            p002_char_len=22,
        ),
    ]
    claude_runs = [
        build_run(
            run_id="claude-1",
            model_id="claude-ops-4.6",
            p001_char_len=90,
            p001_step_count=5,
            p002_char_len=200,
        ),
        build_run(
            run_id="claude-2",
            model_id="claude-ops-4.6",
            p001_char_len=88,
            p001_step_count=4,
            p002_char_len=198,
        ),
    ]
    profiles = [
        build_profile("gpt-5.3", gpt_runs, prompt_weights={"p001": 0.9, "p002": 0.1}),
        build_profile(
            "claude-ops-4.6",
            claude_runs,
            prompt_weights={"p001": 0.9, "p002": 0.1},
        ),
    ]

    calibrator = Calibrator(RepositoryPaths(root=tmp_path))
    artifact = calibrator.calibrate(gpt_runs + claude_runs, profiles)
    path = calibrator.write(artifact)

    assert artifact.suite_id == "fingerprint-suite-v3"
    assert artifact.same_model_stats.mean > artifact.cross_model_stats.mean
    assert (
        artifact.thresholds.match
        >= artifact.thresholds.suspicious
        >= artifact.thresholds.unknown
    )
    assert artifact.coverage_thresholds is not None
    assert artifact.coverage_thresholds.answer_min == 1.0
    assert artifact.coverage_thresholds.reasoning_min == 1.0
    assert artifact.protocol_expectations == {
        "satisfied": True,
        "required_capabilities": ["chat_completions", "visible_reasoning"],
        "issues": [],
    }
    assert path == tmp_path / "calibration" / "fingerprint-suite-v3.json"
    assert json.loads(path.read_text(encoding="utf-8"))["suite_id"] == "fingerprint-suite-v3"
