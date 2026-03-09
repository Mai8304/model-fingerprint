from __future__ import annotations

import pytest

from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.profile_builder import ProfileBuildError, build_profile


def build_run(
    *,
    run_id: str,
    char_len: int,
    reasoning_visible: bool,
    step_count: int | None,
) -> RunArtifact:
    features: dict[str, object] = {
        "answer.char_len": char_len,
        "answer.uses_numbered_list": reasoning_visible,
        "surface.had_markdown_fence": False,
        "transport.reasoning_visible": reasoning_visible,
    }
    if step_count is not None:
        features["reasoning.step_count"] = step_count

    return RunArtifact.model_validate(
        {
            "run_id": run_id,
            "suite_id": "fingerprint-suite-v1",
            "target_label": "gpt-5.3",
            "claimed_model": "gpt-5.3",
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 1.0 if reasoning_visible else 0.0,
            "protocol_compatibility": {
                "satisfied": True,
                "required_capabilities": ["chat_completions"],
                "issues": [],
            },
            "prompts": [
                {
                    "prompt_id": "p001",
                    "status": "completed",
                    "raw_output": "sample",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "reasoning_tokens": 12 if reasoning_visible else 0,
                        "total_tokens": 15,
                    },
                    "features": features,
                }
            ],
        }
    )


def test_profile_builder_aggregates_weighted_multi_channel_statistics() -> None:
    profile = build_profile(
        model_id="gpt-5.3",
        runs=[
            build_run(run_id="run-1", char_len=40, reasoning_visible=True, step_count=2),
            build_run(run_id="run-2", char_len=44, reasoning_visible=False, step_count=None),
            build_run(run_id="run-3", char_len=42, reasoning_visible=True, step_count=3),
        ],
        prompt_weights={"p001": 0.8},
    )

    prompt = profile.prompts[0]

    assert profile.suite_id == "fingerprint-suite-v1"
    assert profile.sample_count == 3
    assert profile.answer_coverage_ratio == 1.0
    assert profile.reasoning_coverage_ratio == pytest.approx(2 / 3)
    assert profile.protocol_expectations == {
        "satisfied": True,
        "required_capabilities": ["chat_completions"],
        "issues": [],
    }
    assert prompt.weight == 0.8
    assert prompt.answer_coverage_ratio == 1.0
    assert prompt.reasoning_coverage_ratio == pytest.approx(2 / 3)
    assert prompt.expected_reasoning_visible == pytest.approx(2 / 3)
    assert prompt.features["answer.char_len"].median == 42.0
    assert prompt.features["answer.char_len"].mad == 2.0
    assert prompt.features["transport.reasoning_visible"].p_true == pytest.approx(2 / 3)
    assert prompt.features["reasoning.step_count"].median == 2.5


def test_profile_builder_rejects_mixed_suite_runs() -> None:
    mixed = build_run(
        run_id="run-mixed",
        char_len=40,
        reasoning_visible=True,
        step_count=2,
    ).model_copy(update={"suite_id": "quick-check-v1"})

    with pytest.raises(ProfileBuildError):
        build_profile(
            model_id="gpt-5.3",
            runs=[
                build_run(run_id="run-1", char_len=40, reasoning_visible=True, step_count=2),
                mixed,
            ],
            prompt_weights={"p001": 0.8},
        )
