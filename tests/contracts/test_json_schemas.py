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
                "id": "p017",
                "name": "concise_architecture_tradeoff",
                "family": "style_brief",
                "intent": "distinguish compact trade-off framing",
                "template": "用不超过120字说明为什么事件溯源不适合作为所有系统的默认架构。",
                "variables": [],
                "output_contract": {"type": "plain_text"},
                "extractor": "style_brief_v1",
                "weight_hint": 0.8,
                "tags": ["style"],
                "risk_level": "low",
            },
            {
                "id": "p017",
                "name": "bad_prompt",
                "family": "creative_mode",
                "intent": "invalid family",
                "template": "x",
                "variables": [],
                "output_contract": {"type": "plain_text"},
                "extractor": "style_brief_v1",
                "weight_hint": 0.8,
                "tags": [],
                "risk_level": "low",
            },
        ),
        (
            "run",
            {
                "run_id": "run-20260309-001",
                "suite_id": "default-v1",
                "target_label": "suspect-a",
                "prompts": [
                    {
                        "prompt_id": "p017",
                        "raw_output": "短答复",
                        "usage": {
                            "input_tokens": 12,
                            "output_tokens": 18,
                            "total_tokens": 30,
                        },
                        "features": {"char_len": 3},
                    }
                ],
            },
            {
                "run_id": "run-20260309-001",
                "suite_id": "screen-v1",
                "target_label": "suspect-a",
                "prompts": [],
            },
        ),
        (
            "profile",
            {
                "model_id": "gpt-5.3",
                "suite_id": "default-v1",
                "sample_count": 5,
                "prompts": [
                    {
                        "prompt_id": "p017",
                        "weight": 0.8,
                        "features": {
                            "char_len": {"kind": "numeric", "median": 42.0, "mad": 4.0},
                        },
                    }
                ],
            },
            {
                "model_id": "gpt-5.3",
                "suite_id": "default-v1",
                "sample_count": 5,
                "prompts": [{"prompt_id": "p017", "weight": 0.8}],
            },
        ),
        (
            "calibration",
            {
                "suite_id": "default-v1",
                "thresholds": {
                    "match": 0.82,
                    "suspicious": 0.71,
                    "unknown": 0.45,
                    "margin": 0.08,
                    "consistency": 0.65,
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
            },
            {
                "suite_id": "default-v1",
                "thresholds": {
                    "match": 1.2,
                    "suspicious": 0.71,
                    "unknown": 0.45,
                    "margin": 0.08,
                    "consistency": 0.65,
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
