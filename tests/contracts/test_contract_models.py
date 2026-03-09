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
        "template": "用不超过120字说明为什么事件溯源不适合作为所有系统的默认架构。",
        "variables": [],
        "output_contract": {"type": "plain_text"},
        "extractor": "style_brief_v1",
        "weight_hint": 0.8,
        "tags": ["style", "architecture", "concise"],
        "risk_level": "low",
    }

    prompt = PromptDefinition.model_validate(payload)

    assert prompt.id == "p017"
    assert prompt.family == "style_brief"


def test_artifact_models_parse_valid_payloads() -> None:
    run = RunArtifact.model_validate(
        {
            "run_id": "run-20260309-001",
            "suite_id": "default-v1",
            "target_label": "suspect-a",
            "claimed_model": "gpt-5.3",
            "prompts": [
                {
                    "prompt_id": "p017",
                    "raw_output": "短答复",
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 18,
                        "total_tokens": 30,
                    },
                    "features": {
                        "char_len": 3,
                        "opens_with_conclusion": True,
                    },
                }
            ],
        }
    )

    profile = ProfileArtifact.model_validate(
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
                        "opens_with_conclusion": {"kind": "boolean", "p_true": 0.9},
                    },
                }
            ],
        }
    )

    calibration = CalibrationArtifact.model_validate(
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
        }
    )

    assert run.suite_id == "default-v1"
    assert profile.prompts[0].features["char_len"].kind == "numeric"
    assert calibration.thresholds.match == 0.82


def test_invalid_prompt_family_is_rejected() -> None:
    with pytest.raises(ValidationError):
        PromptDefinition.model_validate(
            {
                "id": "p017",
                "name": "invalid_family_prompt",
                "family": "creative_mode",
                "intent": "invalid",
                "template": "x",
                "variables": [],
                "output_contract": {"type": "plain_text"},
                "extractor": "style_brief_v1",
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
                "suite_id": "screen-v1",
                "target_label": "suspect-a",
                "prompts": [],
            }
        )

    with pytest.raises(ValidationError):
        RunArtifact.model_validate(
            {
                "run_id": "run-20260309-002",
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
                    }
                ],
            }
        )
