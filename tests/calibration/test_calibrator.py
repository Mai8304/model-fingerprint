from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.calibrator import Calibrator
from modelfingerprint.services.profile_builder import build_profile
from modelfingerprint.settings import RepositoryPaths

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "calibration_runs"


def load_run(name: str) -> RunArtifact:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return RunArtifact.model_validate(payload)


def test_calibrator_builds_thresholds_and_writes_artifact(tmp_path: Path) -> None:
    gpt_runs = [load_run("gpt_run1.json"), load_run("gpt_run2.json")]
    claude_runs = [load_run("claude_run1.json"), load_run("claude_run2.json")]
    profiles = [
        build_profile("gpt-5.3", gpt_runs, prompt_weights={"p001": 0.8}),
        build_profile("claude-ops-4.6", claude_runs, prompt_weights={"p001": 0.8}),
    ]

    calibrator = Calibrator(RepositoryPaths(root=tmp_path))
    artifact = calibrator.calibrate(gpt_runs + claude_runs, profiles)
    path = calibrator.write(artifact)

    assert artifact.suite_id == "default-v1"
    assert artifact.same_model_stats.mean > artifact.cross_model_stats.mean
    assert (
        artifact.thresholds.match
        >= artifact.thresholds.suspicious
        >= artifact.thresholds.unknown
    )
    assert 0.0 <= artifact.thresholds.margin <= 1.0
    assert 0.0 <= artifact.thresholds.consistency <= 1.0
    assert path == tmp_path / "calibration" / "default-v1.json"
    assert json.loads(path.read_text(encoding="utf-8"))["suite_id"] == "default-v1"
