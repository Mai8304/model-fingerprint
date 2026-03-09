from __future__ import annotations

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.comparator import compare_run
from modelfingerprint.services.profile_builder import build_profile
from modelfingerprint.services.verdicts import decide_verdict


def build_run(
    *,
    run_id: str,
    target_label: str,
    model_id: str,
    answer_char_len: int,
    surface_fence: bool,
    reasoning_visible: bool,
) -> RunArtifact:
    features: dict[str, object] = {
        "answer.char_len": answer_char_len,
        "surface.had_markdown_fence": surface_fence,
        "transport.reasoning_visible": reasoning_visible,
    }
    if reasoning_visible:
        features["reasoning.step_count"] = 2

    return RunArtifact.model_validate(
        {
            "run_id": run_id,
            "suite_id": "fingerprint-suite-v1",
            "target_label": target_label,
            "claimed_model": model_id,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 1.0 if reasoning_visible else 0.0,
            "protocol_compatibility": {
                "satisfied": True,
                "required_capabilities": ["chat_completions", "visible_reasoning"],
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


def build_calibration() -> CalibrationArtifact:
    return CalibrationArtifact.model_validate(
        {
            "suite_id": "fingerprint-suite-v1",
            "thresholds": {
                "match": 0.8,
                "suspicious": 0.7,
                "unknown": 0.45,
                "margin": 0.05,
                "consistency": 0.6,
            },
            "coverage_thresholds": {
                "answer_min": 0.8,
                "reasoning_min": 0.5,
            },
            "same_model_stats": {
                "mean": 0.9,
                "p05": 0.8,
                "p50": 0.9,
                "p95": 0.98,
            },
            "cross_model_stats": {
                "mean": 0.35,
                "p05": 0.2,
                "p50": 0.33,
                "p95": 0.45,
            },
            "protocol_expectations": {
                "satisfied": True,
                "required_capabilities": ["chat_completions", "visible_reasoning"],
                "issues": [],
            },
        }
    )


def test_semantically_equivalent_shapes_remain_close_despite_surface_drift() -> None:
    profile = build_profile(
        "gpt-5.3",
        [
            build_run(
                run_id="gpt-1",
                target_label="gpt-5.3",
                model_id="gpt-5.3",
                answer_char_len=40,
                surface_fence=False,
                reasoning_visible=True,
            ),
            build_run(
                run_id="gpt-2",
                target_label="gpt-5.3",
                model_id="gpt-5.3",
                answer_char_len=42,
                surface_fence=False,
                reasoning_visible=True,
            ),
        ],
        prompt_weights={"p001": 1.0},
    )
    target = build_run(
        run_id="suspect-surface-drift",
        target_label="suspect-a",
        model_id="gpt-5.3",
        answer_char_len=41,
        surface_fence=True,
        reasoning_visible=True,
    )

    result = compare_run(target, [profile, profile.model_copy(update={"model_id": "other"})])

    assert result.top1_model == "gpt-5.3"
    assert result.top1_similarity > 0.8
    assert result.protocol_status == "compatible"


def test_hidden_reasoning_flags_protocol_issue_without_forcing_identity_mismatch() -> None:
    profile = build_profile(
        "gpt-5.3",
        [
            build_run(
                run_id="gpt-1",
                target_label="gpt-5.3",
                model_id="gpt-5.3",
                answer_char_len=40,
                surface_fence=False,
                reasoning_visible=True,
            ),
            build_run(
                run_id="gpt-2",
                target_label="gpt-5.3",
                model_id="gpt-5.3",
                answer_char_len=42,
                surface_fence=False,
                reasoning_visible=True,
            ),
        ],
        prompt_weights={"p001": 1.0},
    )
    target = build_run(
        run_id="suspect-hidden-reasoning",
        target_label="suspect-a",
        model_id="gpt-5.3",
        answer_char_len=41,
        surface_fence=False,
        reasoning_visible=False,
    )

    result = compare_run(target, [profile, profile.model_copy(update={"model_id": "other"})])
    verdict = decide_verdict(result, build_calibration())

    assert result.top1_model == "gpt-5.3"
    assert result.protocol_status == "incompatible_protocol"
    assert verdict == "incompatible_protocol"
