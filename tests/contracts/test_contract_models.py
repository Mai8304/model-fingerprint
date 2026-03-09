from __future__ import annotations

import pytest
from pydantic import ValidationError

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import RunArtifact


def test_prompt_definition_parses_valid_payload() -> None:
    payload = {
        "id": "p017",
        "name": "concise_architecture_tradeoff",
        "family": "style_brief",
        "intent": "distinguish compact trade-off framing",
        "messages": [
            {
                "role": "user",
                "content": "用不超过120字说明为什么事件溯源不适合作为所有系统的默认架构。",
            }
        ],
        "generation": {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 120,
            "response_format": "text",
            "reasoning_mode": "capture_if_available",
        },
        "output_contract": {"id": "plain_text_v2", "canonicalizer": "plain_text_v2"},
        "extractors": {
            "answer": "style_brief_v1",
            "reasoning": "reasoning_trace_v1",
            "transport": "completion_metadata_v1",
        },
        "required_capabilities": ["chat_completions"],
        "weight_hint": 0.8,
        "tags": ["style", "architecture", "concise"],
        "risk_level": "low",
    }

    prompt = PromptDefinition.model_validate(payload)

    assert prompt.id == "p017"
    assert prompt.family == "style_brief"
    assert prompt.generation.max_output_tokens == 120
    assert prompt.extractors.answer == "style_brief_v1"


def test_artifact_models_parse_valid_payloads() -> None:
    run = RunArtifact.model_validate(
        {
            "run_id": "run-20260309-001",
            "suite_id": "fingerprint-suite-v1",
            "target_label": "suspect-a",
            "claimed_model": "gpt-5.3",
            "endpoint_profile_id": "openai-chat/deepseek",
            "prompt_count_total": 1,
            "prompt_count_completed": 1,
            "prompt_count_scoreable": 1,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 1.0,
            "protocol_compatibility": {
                "satisfied": True,
                "required_capabilities": ["chat_completions"],
                "issues": [],
            },
            "prompts": [
                {
                    "prompt_id": "p017",
                    "status": "completed",
                    "request_snapshot": {
                        "messages": [{"role": "user", "content": "短答复"}],
                        "generation": {
                            "temperature": 0.0,
                            "top_p": 1.0,
                            "max_output_tokens": 120,
                            "response_format": "text",
                            "reasoning_mode": "capture_if_available",
                        },
                    },
                    "completion": {
                        "answer_text": "短答复",
                        "reasoning_text": "先分析，再回答。",
                        "reasoning_visible": True,
                        "finish_reason": "stop",
                        "latency_ms": 1000,
                        "raw_response_path": (
                            "traces/2026-03-09/run-20260309-001/p017.response.json"
                        ),
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 18,
                            "reasoning_tokens": 24,
                            "total_tokens": 54,
                        },
                    },
                    "canonical_output": {
                        "format_id": "plain_text_v2",
                        "payload": {"text": "短答复"},
                    },
                    "canonicalization_events": [
                        {"code": "normalized_whitespace", "message": "collapsed repeated spaces"}
                    ],
                    "raw_output": "短答复",
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 18,
                        "reasoning_tokens": 24,
                        "total_tokens": 54,
                    },
                    "features": {
                        "answer.char_len": 3,
                        "transport.reasoning_visible": True,
                    },
                }
            ],
        }
    )

    profile = ProfileArtifact.model_validate(
        {
            "model_id": "gpt-5.3",
            "suite_id": "fingerprint-suite-v1",
            "sample_count": 5,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.8,
            "protocol_expectations": {
                "satisfied": True,
                "required_capabilities": ["chat_completions"],
                "issues": [],
            },
            "prompts": [
                {
                    "prompt_id": "p017",
                    "weight": 0.8,
                    "answer_coverage_ratio": 1.0,
                    "reasoning_coverage_ratio": 0.8,
                    "expected_reasoning_visible": 0.8,
                    "features": {
                        "answer.char_len": {"kind": "numeric", "median": 42.0, "mad": 4.0},
                        "transport.reasoning_visible": {"kind": "boolean", "p_true": 0.9},
                    },
                }
            ],
        }
    )

    calibration = CalibrationArtifact.model_validate(
        {
            "suite_id": "fingerprint-suite-v1",
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
                "required_capabilities": ["chat_completions"],
                "issues": [],
            },
        }
    )

    assert run.suite_id == "fingerprint-suite-v1"
    assert run.prompts[0].completion.usage.reasoning_tokens == 24
    assert profile.prompts[0].features["answer.char_len"].kind == "numeric"
    assert calibration.thresholds.match == 0.82


def test_invalid_prompt_family_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PromptDefinition.model_validate(
            {
                "id": "p017",
                "name": "invalid_family_prompt",
                "family": "creative_mode",
                "intent": "invalid",
                "messages": [{"role": "user", "content": "x"}],
                "generation": {
                    "temperature": 0.0,
                    "top_p": 1.0,
                    "max_output_tokens": 120,
                    "response_format": "text",
                    "reasoning_mode": "ignore",
                },
                "output_contract": {"id": "plain_text_v2", "canonicalizer": "plain_text_v2"},
                "extractors": {"answer": "style_brief_v1"},
                "required_capabilities": ["chat_completions"],
                "weight_hint": 0.5,
                "tags": [],
                "risk_level": "low",
            }
        )


def test_invalid_suite_id_and_missing_features_are_rejected() -> None:
    with pytest.raises(ValidationError):
        RunArtifact.model_validate(
            {
                "run_id": "run-20260309-001",
                "suite_id": "quick-check-v0",
                "target_label": "suspect-a",
                "prompts": [],
            }
        )

    with pytest.raises(ValidationError):
        RunArtifact.model_validate(
            {
                "run_id": "run-20260309-002",
                "suite_id": "fingerprint-suite-v1",
                "target_label": "suspect-a",
                "prompt_count_total": 1,
                "prompt_count_completed": 1,
                "prompt_count_scoreable": 1,
                "answer_coverage_ratio": 1.0,
                "reasoning_coverage_ratio": 0.0,
                "protocol_compatibility": {
                    "satisfied": True,
                    "required_capabilities": ["chat_completions"],
                    "issues": [],
                },
                "prompts": [
                    {
                        "prompt_id": "p017",
                        "status": "completed",
                        "raw_output": "短答复",
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 18,
                            "reasoning_tokens": 0,
                            "total_tokens": 30,
                        },
                    }
                ],
            }
        )
