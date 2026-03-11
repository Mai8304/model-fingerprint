from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from modelfingerprint.contracts.schema_export import SCHEMA_EXPORTS

ROOT = Path(__file__).resolve().parents[2]


def load_schema(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


@pytest.mark.parametrize("path", SCHEMA_EXPORTS.values())
def test_exported_schema_files_exist(path: Path) -> None:
    assert path.exists()


@pytest.mark.parametrize(
    ("schema_name", "valid_payload", "invalid_payload"),
    [
        (
            "prompt",
            {
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
                "tags": ["style"],
                "risk_level": "low",
            },
            {
                "id": "p021",
                "name": "bad_prompt",
                "family": "creative_mode",
                "intent": "invalid family",
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
                "weight_hint": 0.8,
                "tags": [],
                "risk_level": "low",
            },
        ),
        (
            "run",
            {
                "run_id": "run-20260309-001",
                "suite_id": "fingerprint-suite-v3",
                "target_label": "suspect-a",
                "prompt_count_total": 1,
                "prompt_count_completed": 1,
                "prompt_count_scoreable": 1,
                "answer_coverage_ratio": 1.0,
                "reasoning_coverage_ratio": 1.0,
                "runtime_policy": {
                    "policy_id": "single_request_progress_runtime_v1",
                    "thinking_probe_status": "supported",
                    "execution_class": "thinking",
                    "no_data_checkpoints_seconds": [30, 60],
                    "progress_poll_interval_seconds": 10,
                    "total_deadline_seconds": 120,
                    "output_token_cap": 3000,
                },
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
                        "canonicalization_events": [],
                        "raw_output": "短答复",
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 18,
                            "reasoning_tokens": 24,
                            "total_tokens": 54,
                        },
                        "attempts": [
                            {
                                "request_attempt_index": 1,
                                "read_timeout_seconds": 30,
                                "output_token_cap": 3000,
                                "status": "completed",
                                "latency_ms": 1000,
                                "finish_reason": "stop",
                                "answer_text_present": True,
                                "reasoning_visible": True,
                                "bytes_received": 256,
                                "first_byte_latency_ms": 1200,
                                "last_progress_latency_ms": 1400,
                                "completed": True,
                            }
                        ],
                        "features": {"answer.char_len": 3},
                    }
                ],
            },
            {
                "run_id": "run-20260309-001",
                "suite_id": "quick-check-v0",
                "target_label": "suspect-a",
                "prompts": [],
            },
        ),
        (
            "profile",
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
                        },
                    }
                ],
            },
            {
                "model_id": "gpt-5.3",
                "suite_id": "fingerprint-suite-v3",
                "sample_count": 5,
                "prompts": [{"prompt_id": "p021", "weight": 0.8}],
            },
        ),
        (
            "calibration",
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
            },
            {
                "suite_id": "fingerprint-suite-v3",
                "thresholds": {
                    "match": 1.2,
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
            },
        ),
        (
            "comparison",
            {
                "schema_version": "comparison.v1",
                "suite_id": "fingerprint-suite-v3",
                "run_id": "suspect-a.fingerprint-suite-v3",
                "target_label": "suspect-a",
                "claimed_model": "gpt-5.3",
                "calibration_id": "fingerprint-suite-v3",
                "summary": {
                    "top1_model": "gpt-5.3",
                    "top1_similarity": 0.93,
                    "top2_model": "claude-ops-4.6",
                    "top2_similarity": 0.74,
                    "margin": 0.19,
                    "consistency": 0.88,
                    "verdict": "match",
                },
                "dimensions": {
                    "content_similarity": 0.9,
                    "capability_similarity": 1.0,
                    "answer_similarity": 0.91,
                    "reasoning_similarity": 0.87,
                    "transport_similarity": 0.84,
                    "surface_similarity": 0.99,
                },
                "coverage": {
                    "answer_coverage_ratio": 1.0,
                    "reasoning_coverage_ratio": 1.0,
                    "capability_coverage_ratio": 1.0,
                    "protocol_status": "compatible",
                },
                "diagnostics": {
                    "protocol_issues": [],
                    "hard_mismatches": [],
                },
                "candidates": [
                    {
                        "model_id": "gpt-5.3",
                        "overall_similarity": 0.93,
                        "content_similarity": 0.9,
                        "capability_similarity": 1.0,
                        "answer_similarity": 0.91,
                        "reasoning_similarity": 0.87,
                        "transport_similarity": 0.84,
                        "surface_similarity": 0.99,
                        "consistency": 1.0,
                        "answer_coverage_ratio": 1.0,
                        "reasoning_coverage_ratio": 1.0,
                        "capability_coverage_ratio": 1.0,
                        "protocol_status": "compatible",
                        "protocol_issues": [],
                        "hard_mismatches": [],
                        "prompt_scores": {"p021": 0.95},
                    }
                ],
                "prompt_breakdown": [
                    {
                        "prompt_id": "p021",
                        "status": "completed",
                        "similarity": 0.95,
                        "scoreable": True,
                    }
                ],
                "capability_breakdown": [
                    {
                        "capability": "thinking",
                        "weight": 0.35,
                        "observed_status": "supported",
                        "expected_distribution": {"supported": 1.0},
                        "similarity": 1.0,
                    }
                ],
                "thresholds_used": {
                    "match": 0.82,
                    "suspicious": 0.71,
                    "unknown": 0.45,
                    "margin": 0.08,
                    "consistency": 0.65,
                    "answer_min": 0.8,
                    "reasoning_min": 0.3,
                },
            },
            {
                "schema_version": "comparison.v1",
                "suite_id": "fingerprint-suite-v3",
                "run_id": "suspect-a.fingerprint-suite-v3",
                "target_label": "suspect-a",
                "calibration_id": "fingerprint-suite-v3",
                "summary": {
                    "top1_model": "gpt-5.3",
                    "top1_similarity": 1.4,
                    "top2_model": "claude-ops-4.6",
                    "top2_similarity": 0.74,
                    "margin": 0.19,
                    "consistency": 0.88,
                    "verdict": "match",
                },
                "dimensions": {
                    "content_similarity": 0.9,
                    "capability_similarity": 1.0,
                    "answer_similarity": 0.91,
                    "reasoning_similarity": 0.87,
                    "transport_similarity": 0.84,
                    "surface_similarity": 0.99,
                },
                "coverage": {
                    "answer_coverage_ratio": 1.0,
                    "reasoning_coverage_ratio": 1.0,
                    "capability_coverage_ratio": 1.0,
                    "protocol_status": "compatible",
                },
                "diagnostics": {
                    "protocol_issues": [],
                    "hard_mismatches": [],
                },
                "candidates": [],
                "prompt_breakdown": [],
                "capability_breakdown": [],
                "thresholds_used": {
                    "match": 0.82,
                    "suspicious": 0.71,
                    "unknown": 0.45,
                    "margin": 0.08,
                    "consistency": 0.65,
                    "answer_min": 0.8,
                    "reasoning_min": 0.3,
                },
            },
        ),
    ],
)
def test_json_schemas_validate_expected_payloads(
    schema_name: str,
    valid_payload: dict[str, object],
    invalid_payload: dict[str, object],
) -> None:
    validator = Draft202012Validator(load_schema(ROOT / SCHEMA_EXPORTS[schema_name]))

    assert list(validator.iter_errors(valid_payload)) == []
    assert list(validator.iter_errors(invalid_payload)) != []
