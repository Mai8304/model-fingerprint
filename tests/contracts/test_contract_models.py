from __future__ import annotations

import pytest
from pydantic import ValidationError

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import RunArtifact


def test_prompt_definition_parses_valid_payload() -> None:
    payload = {
        "id": "p021",
        "name": "concise_architecture_tradeoff",
        "family": "evidence_grounding",
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
        "output_contract": {"id": "tolerant_json_v3", "canonicalizer": "tolerant_json_v3"},
        "extractors": {
            "answer": "evidence_grounding_v3",
            "reasoning": "reasoning_trace_v1",
            "transport": "completion_metadata_v1",
        },
        "required_capabilities": ["chat_completions"],
        "weight_hint": 0.8,
        "tags": ["style", "architecture", "concise"],
        "risk_level": "low",
    }

    prompt = PromptDefinition.model_validate(payload)

    assert prompt.id == "p021"
    assert prompt.family == "evidence_grounding"
    assert prompt.generation.max_output_tokens == 120
    assert prompt.extractors.answer == "evidence_grounding_v3"


def test_prompt_definition_supports_evaluation_and_score_extractor() -> None:
    payload = {
        "id": "p024",
        "name": "evidence_bound_identity_resolution",
        "family": "evidence_grounding",
        "intent": "measure grounded extraction with explicit abstention",
        "messages": [
            {
                "role": "system",
                "content": "Return JSON only and keep unknown values as null.",
            },
            {
                "role": "user",
                "content": "Resolve the current owner, role, and region from the supplied memo.",
            },
        ],
        "generation": {
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 240,
            "response_format": "text",
            "reasoning_mode": "capture_if_available",
        },
        "output_contract": {"id": "tolerant_json_v3", "canonicalizer": "tolerant_json_v3"},
        "extractors": {
            "answer": "evidence_grounding_v3",
            "score": "evidence_grounding_score_v3",
            "reasoning": "reasoning_trace_v1",
            "transport": "completion_metadata_v1",
        },
        "evaluation": {
            "reference": {
                "expected_task_result": {
                    "owner": "Alice Wong",
                    "role": "Primary DBA",
                    "region": None,
                }
            }
        },
        "required_capabilities": ["chat_completions"],
        "weight_hint": 0.95,
        "tags": ["evidence", "abstain", "v3"],
        "risk_level": "low",
    }

    prompt = PromptDefinition.model_validate(payload)

    assert prompt.id == "p024"
    assert prompt.family == "evidence_grounding"
    assert prompt.extractors.score == "evidence_grounding_score_v3"
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference["expected_task_result"]["owner"] == "Alice Wong"


def test_artifact_models_parse_valid_payloads() -> None:
    run = RunArtifact.model_validate(
        {
            "run_id": "run-20260309-001",
            "suite_id": "fingerprint-suite-v3",
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
                    "prompt_id": "p021",
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
                            "traces/2026-03-09/run-20260309-001/p021.response.json"
                        ),
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 18,
                            "reasoning_tokens": 24,
                            "total_tokens": 54,
                        },
                    },
                    "canonical_output": {
                        "format_id": "tolerant_json_v3",
                        "payload": {
                            "task_result": {"owner": "Alice Wong"},
                            "evidence": {"owner": ["e1"]},
                            "unknowns": {},
                            "violations": [],
                        },
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
            "suite_id": "fingerprint-suite-v3",
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
                    "prompt_id": "p021",
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
                "required_capabilities": ["chat_completions"],
                "issues": [],
            },
        }
    )

    assert run.suite_id == "fingerprint-suite-v3"
    assert run.prompts[0].completion.usage.reasoning_tokens == 24
    assert profile.prompts[0].features["answer.char_len"].kind == "numeric"
    assert calibration.thresholds.match == 0.82


def test_run_artifact_accepts_score_channel_features() -> None:
    run = RunArtifact.model_validate(
        {
            "run_id": "run-20260309-011",
            "suite_id": "fingerprint-suite-v3",
            "target_label": "suspect-state",
            "prompt_count_total": 1,
            "prompt_count_completed": 1,
            "prompt_count_scoreable": 1,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "prompts": [
                {
                    "prompt_id": "p024",
                    "status": "completed",
                    "raw_output": "{\"task_result\": {}}",
                    "usage": {
                        "input_tokens": 20,
                        "output_tokens": 30,
                        "reasoning_tokens": 0,
                        "total_tokens": 50,
                    },
                    "features": {
                        "score.value_accuracy": 1.0,
                        "score.abstention_compliance": 1.0,
                        "answer.filled_field_count": 2,
                        "transport.reasoning_visible": False,
                    },
                }
            ],
        }
    )

    assert run.suite_id == "fingerprint-suite-v3"
    assert run.prompts[0].features["score.value_accuracy"] == 1.0


def test_artifact_models_parse_capability_probe_sections() -> None:
    run = RunArtifact.model_validate(
        {
            "run_id": "run-20260310-capability",
            "suite_id": "fingerprint-suite-v3",
            "target_label": "suspect-capability",
            "prompt_count_total": 1,
            "prompt_count_completed": 1,
            "prompt_count_scoreable": 1,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "capability_probe": {
                "probe_mode": "minimal",
                "probe_version": "v1",
                "coverage_ratio": 0.75,
                "capabilities": {
                    "thinking": {
                        "status": "supported",
                        "detail": "reasoning field is populated",
                        "http_status": 200,
                        "latency_ms": 1500,
                        "evidence": {"field": "reasoning"},
                    },
                    "tools": {
                        "status": "insufficient_evidence",
                        "detail": "provider returned 429",
                        "http_status": 429,
                        "latency_ms": 1200,
                        "evidence": {"retry_after_seconds": 60},
                    },
                },
            },
            "prompts": [
                {
                    "prompt_id": "p024",
                    "status": "completed",
                    "raw_output": "{\"task_result\": {}}",
                    "usage": {
                        "input_tokens": 20,
                        "output_tokens": 30,
                        "reasoning_tokens": 0,
                        "total_tokens": 50,
                    },
                    "features": {
                        "score.value_accuracy": 1.0,
                        "answer.filled_field_count": 2,
                    },
                }
            ],
        }
    )

    profile = ProfileArtifact.model_validate(
        {
            "model_id": "glm-5",
            "suite_id": "fingerprint-suite-v3",
            "sample_count": 3,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.3,
                "capability_profile": {
                    "coverage_ratio": 0.9,
                    "capabilities": {
                        "thinking": {
                            "distribution": {
                                "supported": 1.0,
                            },
                        },
                        "tools": {
                            "distribution": {
                                "supported": 0.67,
                                "insufficient_evidence": 0.33,
                            },
                        },
                    },
                },
            "prompts": [
                {
                    "prompt_id": "p024",
                    "weight": 1.0,
                    "features": {
                        "score.value_accuracy": {"kind": "numeric", "median": 1.0, "mad": 0.1},
                    },
                }
            ],
        }
    )

    assert run.capability_probe is not None
    assert run.capability_probe.capabilities["thinking"].status == "supported"
    assert profile.capability_profile is not None
    assert profile.capability_profile.capabilities["thinking"].distribution["supported"] == 1.0


def test_capability_probe_accepts_split_image_and_vision_ids() -> None:
    run = RunArtifact.model_validate(
        {
            "run_id": "run-20260311-capability-split",
            "suite_id": "fingerprint-suite-v3",
            "target_label": "suspect-capability-split",
            "prompt_count_total": 1,
            "prompt_count_completed": 1,
            "prompt_count_scoreable": 1,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "capability_probe": {
                "probe_mode": "minimal",
                "probe_version": "v2",
                "coverage_ratio": 1.0,
                "capabilities": {
                    "thinking": {"status": "supported"},
                    "tools": {"status": "supported"},
                    "streaming": {"status": "supported"},
                    "image_generation": {"status": "supported"},
                    "vision_understanding": {"status": "accepted_but_ignored"},
                },
            },
            "prompts": [
                {
                    "prompt_id": "p024",
                    "status": "completed",
                    "raw_output": "{\"task_result\": {}}",
                    "usage": {
                        "input_tokens": 20,
                        "output_tokens": 30,
                        "reasoning_tokens": 0,
                        "total_tokens": 50,
                    },
                    "features": {
                        "score.value_accuracy": 1.0,
                        "answer.filled_field_count": 2,
                    },
                }
            ],
        }
    )

    profile = ProfileArtifact.model_validate(
        {
            "model_id": "nano-banana",
            "suite_id": "fingerprint-suite-v3",
            "sample_count": 1,
            "capability_profile": {
                "coverage_ratio": 1.0,
                "capabilities": {
                    "image_generation": {"distribution": {"supported": 1.0}},
                    "vision_understanding": {
                        "distribution": {"accepted_but_ignored": 1.0}
                    },
                },
            },
            "prompts": [
                {
                    "prompt_id": "p024",
                    "weight": 1.0,
                    "features": {
                        "score.value_accuracy": {"kind": "numeric", "median": 1.0, "mad": 0.1},
                    },
                }
            ],
        }
    )

    assert run.capability_probe is not None
    assert run.capability_probe.capabilities["image_generation"].status == "supported"
    assert profile.capability_profile is not None
    assert (
        profile.capability_profile.capabilities["vision_understanding"].distribution[
            "accepted_but_ignored"
        ]
        == 1.0
    )


def test_capability_probe_rejects_legacy_image_id() -> None:
    with pytest.raises(ValidationError):
        RunArtifact.model_validate(
            {
                "run_id": "run-20260311-legacy-image",
                "suite_id": "fingerprint-suite-v3",
                "target_label": "legacy-image",
                "capability_probe": {
                    "probe_mode": "minimal",
                    "probe_version": "v1",
                    "coverage_ratio": 1.0,
                    "capabilities": {
                        "image": {"status": "supported"},
                    },
                },
                "prompts": [
                    {
                        "prompt_id": "p024",
                        "status": "completed",
                        "raw_output": "{\"task_result\": {}}",
                        "usage": {
                            "input_tokens": 20,
                            "output_tokens": 30,
                            "reasoning_tokens": 0,
                            "total_tokens": 50,
                        },
                        "features": {
                            "score.value_accuracy": 1.0,
                        },
                    }
                ],
            }
        )


def test_invalid_prompt_family_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PromptDefinition.model_validate(
            {
                "id": "p021",
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
                "output_contract": {"id": "tolerant_json_v3", "canonicalizer": "tolerant_json_v3"},
                "extractors": {"answer": "evidence_grounding_v3"},
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
                "suite_id": "fingerprint-suite-v3",
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
                        "prompt_id": "p021",
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
