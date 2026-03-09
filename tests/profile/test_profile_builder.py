from __future__ import annotations

import json
from pathlib import Path

import pytest

from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.profile_builder import ProfileBuildError, build_profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "profile_runs"


def load_run(name: str) -> RunArtifact:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return RunArtifact.model_validate(payload)


def test_profile_builder_aggregates_runs_with_robust_statistics() -> None:
    profile = build_profile(
        model_id="gpt-5.3",
        runs=[load_run("run1.json"), load_run("run2.json"), load_run("run3.json")],
        prompt_weights={"p001": 0.8},
    )

    prompt = profile.prompts[0]

    assert profile.suite_id == "default-v1"
    assert profile.sample_count == 3
    assert prompt.weight == 0.8
    assert prompt.features["char_len"].median == 42.0
    assert prompt.features["char_len"].mad == 2.0
    assert prompt.features["uses_numbered_list"].p_true == pytest.approx(2 / 3)
    assert prompt.features["abstraction_level"].distribution == pytest.approx(
        {"concrete": 2 / 3, "abstract": 1 / 3}
    )


def test_profile_builder_rejects_mixed_suite_runs() -> None:
    mixed = load_run("run1.json").model_copy(update={"suite_id": "screening-v1"})

    with pytest.raises(ProfileBuildError):
        build_profile(
            model_id="gpt-5.3",
            runs=[load_run("run1.json"), mixed],
            prompt_weights={"p001": 0.8},
        )
