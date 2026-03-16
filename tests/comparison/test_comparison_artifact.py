from __future__ import annotations

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.comparison import ComparisonArtifact
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.comparison_artifact import build_comparison_artifact
from modelfingerprint.services.profile_builder import build_profile


def build_run(
    *,
    run_id: str,
    target_label: str,
    claimed_model: str | None,
    p021_char_len: int,
    p021_step_count: int | None,
    p021_reasoning_visible: bool,
    p023_char_len: int,
    capability_status: str,
    answer_coverage_ratio: float = 1.0,
    reasoning_coverage_ratio: float = 1.0,
) -> RunArtifact:
    prompt1_features: dict[str, object] = {
        "answer.char_len": p021_char_len,
        "transport.reasoning_visible": p021_reasoning_visible,
        "surface.had_markdown_fence": False,
    }
    if p021_step_count is not None:
        prompt1_features["reasoning.step_count"] = p021_step_count

    return RunArtifact.model_validate(
        {
            "run_id": run_id,
            "suite_id": "fingerprint-suite-v3",
            "target_label": target_label,
            "claimed_model": claimed_model,
            "answer_coverage_ratio": answer_coverage_ratio,
            "reasoning_coverage_ratio": reasoning_coverage_ratio,
            "capability_probe": {
                "probe_mode": "minimal",
                "probe_version": "v1",
                "coverage_ratio": 1.0,
                "capabilities": {
                    "thinking": {
                        "status": capability_status,
                        "detail": "visible reasoning",
                        "evidence": {"field": "reasoning"},
                    },
                    "tools": {
                        "status": "supported",
                        "detail": "tool_calls returned",
                        "evidence": {"field": "tool_calls"},
                    },
                    "image_generation": {
                        "status": "supported",
                        "detail": "image returned",
                        "evidence": {"asset_field": "choices.0.message.images.0.image_url.url"},
                    },
                    "vision_understanding": {
                        "status": "accepted_but_ignored",
                        "detail": "recognized grounded answer: red",
                        "evidence": {"normalized_answer": "red"},
                    },
                },
            },
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
                        "reasoning_tokens": 12 if p021_reasoning_visible else 0,
                        "total_tokens": 15,
                    },
                    "completion": {
                        "answer_text": "sample-p021",
                        "reasoning_text": "1. inspect\n2. answer"
                        if p021_reasoning_visible
                        else None,
                        "reasoning_visible": p021_reasoning_visible,
                        "finish_reason": "stop",
                        "usage": {
                            "input_tokens": 10,
                            "output_tokens": 5,
                            "reasoning_tokens": 12 if p021_reasoning_visible else 0,
                            "total_tokens": 15,
                        },
                    },
                    "features": prompt1_features,
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


def build_calibration() -> CalibrationArtifact:
    return CalibrationArtifact.model_validate(
        {
            "suite_id": "fingerprint-suite-v3",
            "thresholds": {
                "match": 0.82,
                "suspicious": 0.71,
                "unknown": 0.45,
                "margin": 0.08,
                "consistency": 0.65,
            },
            "coverage_thresholds": {
                "answer_min": 0.8,
                "reasoning_min": 0.3,
            },
            "same_model_stats": {
                "mean": 0.88,
                "p05": 0.79,
                "p50": 0.89,
                "p95": 0.96,
            },
            "cross_model_stats": {
                "mean": 0.41,
                "p05": 0.22,
                "p50": 0.39,
                "p95": 0.61,
            },
            "protocol_expectations": {
                "satisfied": True,
                "required_capabilities": ["chat_completions", "visible_reasoning"],
                "issues": [],
            },
        }
    )


def build_profiles() -> list[ProfileArtifact]:
    gpt_runs = [
        build_run(
            run_id="gpt-1",
            target_label="gpt-5.3",
            claimed_model="gpt-5.3",
            p021_char_len=40,
            p021_step_count=2,
            p021_reasoning_visible=True,
            p023_char_len=20,
            capability_status="supported",
        ),
        build_run(
            run_id="gpt-2",
            target_label="gpt-5.3",
            claimed_model="gpt-5.3",
            p021_char_len=42,
            p021_step_count=2,
            p021_reasoning_visible=True,
            p023_char_len=22,
            capability_status="supported",
        ),
    ]
    claude_runs = [
        build_run(
            run_id="claude-1",
            target_label="claude-ops-4.6",
            claimed_model="claude-ops-4.6",
            p021_char_len=90,
            p021_step_count=5,
            p021_reasoning_visible=True,
            p023_char_len=200,
            capability_status="accepted_but_ignored",
        ),
        build_run(
            run_id="claude-2",
            target_label="claude-ops-4.6",
            claimed_model="claude-ops-4.6",
            p021_char_len=88,
            p021_step_count=4,
            p021_reasoning_visible=True,
            p023_char_len=198,
            capability_status="accepted_but_ignored",
        ),
    ]
    return [
        build_profile("gpt-5.3", gpt_runs, prompt_weights={"p021": 0.9, "p023": 0.1}),
        build_profile("claude-ops-4.6", claude_runs, prompt_weights={"p021": 0.9, "p023": 0.1}),
    ]


def test_build_comparison_artifact_emits_ranked_candidates_and_breakdowns() -> None:
    target = build_run(
        run_id="suspect-a",
        target_label="suspect-a",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p021_reasoning_visible=True,
        p023_char_len=199,
        capability_status="supported",
    )

    artifact = build_comparison_artifact(
        run=target,
        profiles=build_profiles(),
        calibration=build_calibration(),
    )

    assert isinstance(artifact, ComparisonArtifact)
    assert artifact.schema_version == "comparison.v1"
    assert artifact.summary.top1_model == "gpt-5.3"
    assert artifact.summary.verdict == "match"
    assert len(artifact.candidates) == 2
    assert artifact.candidates[0].model_id == "gpt-5.3"
    assert (
        artifact.candidates[0].prompt_scores["p021"]
        > artifact.candidates[1].prompt_scores["p021"]
    )
    assert artifact.prompt_breakdown[0].prompt_id == "p021"
    assert artifact.prompt_breakdown[0].status == "completed"
    assert artifact.prompt_breakdown[0].similarity is not None
    capability_names = [item.capability for item in artifact.capability_breakdown]
    assert capability_names[:4] == [
        "thinking",
        "tools",
        "image_generation",
        "vision_understanding",
    ]
    assert artifact.capability_breakdown[0].observed_status == "supported"
    assert artifact.thresholds_used.match == 0.82
