from __future__ import annotations

import pytest

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.comparator import compare_run
from modelfingerprint.services.profile_builder import build_profile
from modelfingerprint.services.verdicts import decide_verdict


def build_run(
    *,
    run_id: str,
    target_label: str,
    claimed_model: str | None,
    p021_char_len: int,
    p021_step_count: int | None,
    p021_reasoning_visible: bool,
    p023_char_len: int,
    p021_latency_bucket_ms: int | None = None,
    p021_extra_features: dict[str, object] | None = None,
    answer_coverage_ratio: float = 1.0,
    reasoning_coverage_ratio: float = 1.0,
    capability_probe: dict[str, object] | None = None,
) -> RunArtifact:
    prompt1_features: dict[str, object] = {
        "answer.char_len": p021_char_len,
        "transport.reasoning_visible": p021_reasoning_visible,
        "surface.had_markdown_fence": False,
    }
    if p021_step_count is not None:
        prompt1_features["reasoning.step_count"] = p021_step_count
    if p021_latency_bucket_ms is not None:
        prompt1_features["transport.latency_bucket_ms"] = p021_latency_bucket_ms
    if p021_extra_features is not None:
        prompt1_features.update(p021_extra_features)

    prompt1_completion = None
    if p021_reasoning_visible:
        prompt1_completion = {
            "answer_text": "sample-p021",
            "reasoning_text": "1. inspect\n2. answer",
            "reasoning_visible": True,
            "finish_reason": "stop",
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5,
                "reasoning_tokens": 12,
                "total_tokens": 15,
            },
        }

    prompts = [
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
            "completion": prompt1_completion,
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
    ]
    return RunArtifact.model_validate(
        {
            "run_id": run_id,
            "suite_id": "fingerprint-suite-v3",
            "target_label": target_label,
            "claimed_model": claimed_model,
            "answer_coverage_ratio": answer_coverage_ratio,
            "reasoning_coverage_ratio": reasoning_coverage_ratio,
            "capability_probe": capability_probe,
            "protocol_compatibility": {
                "satisfied": True,
                "required_capabilities": ["chat_completions", "visible_reasoning"],
                "issues": [],
            },
            "prompts": prompts,
        }
    )


def build_calibration() -> CalibrationArtifact:
    return CalibrationArtifact.model_validate(
        {
            "suite_id": "fingerprint-suite-v3",
            "thresholds": {
                "match": 0.82,
                "suspicious": 0.7,
                "unknown": 0.45,
                "margin": 0.05,
                "consistency": 0.65,
            },
            "coverage_thresholds": {
                "answer_min": 0.8,
                "reasoning_min": 0.5,
            },
            "same_model_stats": {
                "mean": 0.92,
                "p05": 0.82,
                "p50": 0.91,
                "p95": 0.98,
            },
            "cross_model_stats": {
                "mean": 0.34,
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


def test_comparator_uses_prompt_weights_and_emits_coverage_fields() -> None:
    gpt_runs = [
        build_run(
            run_id="gpt-1",
            target_label="gpt-5.3",
            claimed_model="gpt-5.3",
            p021_char_len=40,
            p021_step_count=2,
            p021_reasoning_visible=True,
            p023_char_len=20,
        ),
        build_run(
            run_id="gpt-2",
            target_label="gpt-5.3",
            claimed_model="gpt-5.3",
            p021_char_len=42,
            p021_step_count=2,
            p021_reasoning_visible=True,
            p023_char_len=22,
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
        ),
        build_run(
            run_id="claude-2",
            target_label="claude-ops-4.6",
            claimed_model="claude-ops-4.6",
            p021_char_len=88,
            p021_step_count=4,
            p021_reasoning_visible=True,
            p023_char_len=198,
        ),
    ]
    profiles = [
        build_profile("gpt-5.3", gpt_runs, prompt_weights={"p021": 0.9, "p023": 0.1}),
        build_profile(
            "claude-ops-4.6",
            claude_runs,
            prompt_weights={"p021": 0.9, "p023": 0.1},
        ),
    ]
    target = build_run(
        run_id="suspect-a",
        target_label="suspect-a",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p021_reasoning_visible=True,
        p023_char_len=199,
    )

    result = compare_run(target, profiles)

    assert result.top1_model == "gpt-5.3"
    assert result.top2_model == "claude-ops-4.6"
    assert result.top1_similarity > result.top2_similarity
    assert result.claimed_model_similarity == result.top1_similarity
    assert result.answer_similarity is not None
    assert result.reasoning_similarity is not None
    assert result.answer_coverage_ratio == 1.0
    assert result.reasoning_coverage_ratio == 1.0
    assert result.capability_similarity is None
    assert result.capability_coverage_ratio == 0.0
    assert result.hard_mismatches == ()
    assert result.protocol_status == "compatible"


def test_low_answer_coverage_becomes_insufficient_evidence() -> None:
    profile = build_profile(
        "gpt-5.3",
        [
            build_run(
                run_id="gpt-1",
                target_label="gpt-5.3",
                claimed_model="gpt-5.3",
                p021_char_len=40,
                p021_step_count=2,
                p021_reasoning_visible=True,
                p023_char_len=20,
            ),
            build_run(
                run_id="gpt-2",
                target_label="gpt-5.3",
                claimed_model="gpt-5.3",
                p021_char_len=42,
                p021_step_count=2,
                p021_reasoning_visible=True,
                p023_char_len=22,
            ),
        ],
        prompt_weights={"p021": 0.9, "p023": 0.1},
    )
    target = build_run(
        run_id="suspect-low-coverage",
        target_label="suspect-a",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p021_reasoning_visible=True,
        p023_char_len=21,
        answer_coverage_ratio=0.5,
        reasoning_coverage_ratio=1.0,
    )

    verdict = decide_verdict(compare_run(target, [profile, profile]), build_calibration())

    assert verdict == "insufficient_evidence"


def test_comparator_uses_score_channel_when_available() -> None:
    profile_a = ProfileArtifact.model_validate(
        {
            "model_id": "model-a",
            "suite_id": "fingerprint-suite-v3",
            "sample_count": 2,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "prompts": [
                {
                    "prompt_id": "p024",
                    "weight": 1.0,
                    "features": {
                        "score.value_accuracy": {"kind": "numeric", "median": 1.0, "mad": 0.01},
                        "answer.filled_field_count": {"kind": "numeric", "median": 3.0, "mad": 0.1},
                    },
                }
            ],
        }
    )
    profile_b = ProfileArtifact.model_validate(
        {
            "model_id": "model-b",
            "suite_id": "fingerprint-suite-v3",
            "sample_count": 2,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "prompts": [
                {
                    "prompt_id": "p024",
                    "weight": 1.0,
                    "features": {
                        "score.value_accuracy": {"kind": "numeric", "median": 0.0, "mad": 0.01},
                        "answer.filled_field_count": {"kind": "numeric", "median": 3.0, "mad": 0.1},
                    },
                }
            ],
        }
    )
    target = RunArtifact.model_validate(
        {
            "run_id": "suspect-score",
            "suite_id": "fingerprint-suite-v3",
            "target_label": "suspect-score",
            "claimed_model": "model-a",
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "prompts": [
                {
                    "prompt_id": "p024",
                    "status": "completed",
                    "raw_output": "{\"task_result\": {}}",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 10,
                        "reasoning_tokens": 0,
                        "total_tokens": 20,
                    },
                    "features": {
                        "score.value_accuracy": 1.0,
                        "answer.filled_field_count": 3,
                    },
                }
            ],
        }
    )

    result = compare_run(target, [profile_a, profile_b])

    assert result.top1_model == "model-a"
    assert result.top1_similarity > result.top2_similarity


def test_comparator_scores_capability_similarity_when_probe_and_profile_exist() -> None:
    profile = ProfileArtifact.model_validate(
        {
            "model_id": "glm-5",
            "suite_id": "fingerprint-suite-v3",
            "sample_count": 2,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "capability_profile": {
                "coverage_ratio": 1.0,
                "capabilities": {
                    "thinking": {"distribution": {"supported": 1.0}},
                    "tools": {"distribution": {"supported": 1.0}},
                    "streaming": {"distribution": {"supported": 1.0}},
                    "image_generation": {"distribution": {"supported": 1.0}},
                    "vision_understanding": {"distribution": {"supported": 1.0}},
                },
            },
            "prompts": [
                {
                    "prompt_id": "p024",
                    "weight": 1.0,
                    "features": {
                        "score.value_accuracy": {"kind": "numeric", "median": 1.0, "mad": 0.01},
                    },
                }
            ],
        }
    )
    target = RunArtifact.model_validate(
        {
            "run_id": "suspect-capability",
            "suite_id": "fingerprint-suite-v3",
            "target_label": "suspect-capability",
            "claimed_model": "glm-5",
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "capability_probe": {
                "probe_mode": "minimal",
                "probe_version": "v2",
                "coverage_ratio": 1.0,
                "capabilities": {
                    "thinking": {"status": "supported", "evidence": {}},
                    "tools": {"status": "supported", "evidence": {}},
                    "streaming": {"status": "supported", "evidence": {}},
                    "image_generation": {"status": "supported", "evidence": {}},
                    "vision_understanding": {
                        "status": "accepted_but_ignored",
                        "evidence": {},
                    },
                },
            },
            "prompts": [
                {
                    "prompt_id": "p024",
                    "status": "completed",
                    "raw_output": "{\"task_result\": {}}",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 10,
                        "reasoning_tokens": 0,
                        "total_tokens": 20,
                    },
                    "features": {
                        "score.value_accuracy": 1.0,
                    },
                }
            ],
        }
    )

    result = compare_run(target, [profile])

    assert result.capability_similarity == pytest.approx(0.9325)
    assert result.capability_coverage_ratio == 1.0


def test_transport_latency_bucket_does_not_affect_identity_similarity() -> None:
    profile = build_profile(
        "gpt-5.3",
        [
            build_run(
                run_id="gpt-1",
                target_label="gpt-5.3",
                claimed_model="gpt-5.3",
                p021_char_len=40,
                p021_step_count=2,
                p021_reasoning_visible=True,
                p021_latency_bucket_ms=1000,
                p023_char_len=20,
            ),
            build_run(
                run_id="gpt-2",
                target_label="gpt-5.3",
                claimed_model="gpt-5.3",
                p021_char_len=42,
                p021_step_count=2,
                p021_reasoning_visible=True,
                p021_latency_bucket_ms=2000,
                p023_char_len=22,
            ),
        ],
        prompt_weights={"p021": 0.9, "p023": 0.1},
    )

    fast_target = build_run(
        run_id="suspect-fast",
        target_label="suspect-fast",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p021_reasoning_visible=True,
        p021_latency_bucket_ms=1000,
        p023_char_len=21,
    )
    slow_target = build_run(
        run_id="suspect-slow",
        target_label="suspect-slow",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p021_reasoning_visible=True,
        p021_latency_bucket_ms=120000,
        p023_char_len=21,
    )

    fast_result = compare_run(fast_target, [profile])
    slow_result = compare_run(slow_target, [profile])

    assert fast_result.top1_similarity == pytest.approx(slow_result.top1_similarity)
    assert fast_result.transport_similarity == pytest.approx(slow_result.transport_similarity)


def test_removed_runtime_coupled_features_do_not_affect_identity_similarity() -> None:
    profile = build_profile(
        "gpt-5.3",
        [
            build_run(
                run_id="gpt-1",
                target_label="gpt-5.3",
                claimed_model="gpt-5.3",
                p021_char_len=40,
                p021_step_count=2,
                p021_reasoning_visible=True,
                p023_char_len=20,
                p021_extra_features={
                    "transport.reasoning_tokens": 12,
                    "transport.finish_reason": "stop",
                    "surface.field_order_match": True,
                    "surface.key_alias_normalized": False,
                },
            ),
            build_run(
                run_id="gpt-2",
                target_label="gpt-5.3",
                claimed_model="gpt-5.3",
                p021_char_len=42,
                p021_step_count=2,
                p021_reasoning_visible=True,
                p023_char_len=22,
                p021_extra_features={
                    "transport.reasoning_tokens": 18,
                    "transport.finish_reason": "length",
                    "surface.field_order_match": False,
                    "surface.key_alias_normalized": True,
                },
            ),
        ],
        prompt_weights={"p021": 0.9, "p023": 0.1},
    )

    clean_target = build_run(
        run_id="suspect-clean",
        target_label="suspect-clean",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p021_reasoning_visible=True,
        p023_char_len=21,
        p021_extra_features={
            "transport.reasoning_tokens": 10,
            "transport.finish_reason": "stop",
            "surface.field_order_match": True,
            "surface.key_alias_normalized": False,
            "surface.had_markdown_fence": False,
        },
    )
    noisy_target = build_run(
        run_id="suspect-noisy",
        target_label="suspect-noisy",
        claimed_model="gpt-5.3",
        p021_char_len=41,
        p021_step_count=2,
        p021_reasoning_visible=True,
        p023_char_len=21,
        p021_extra_features={
            "transport.reasoning_tokens": 999,
            "transport.finish_reason": "tool_calls",
            "surface.field_order_match": False,
            "surface.key_alias_normalized": True,
            "surface.had_markdown_fence": True,
        },
    )

    clean_result = compare_run(clean_target, [profile])
    noisy_result = compare_run(noisy_target, [profile])

    assert clean_result.top1_similarity == pytest.approx(noisy_result.top1_similarity)
    assert clean_result.transport_similarity == pytest.approx(noisy_result.transport_similarity)
    assert clean_result.surface_similarity == pytest.approx(noisy_result.surface_similarity)
