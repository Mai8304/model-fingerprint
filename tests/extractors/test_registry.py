from __future__ import annotations

from pathlib import Path

import pytest

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import ExtractorDescriptor, ExtractorValidationError
from modelfingerprint.extractors.registry import ExtractorRegistry

ROOT = Path(__file__).resolve().parents[2]


def build_prompt(extractor: str, score_extractor: str | None = None) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p001",
            "name": "evidence_bound_identity_resolution",
            "family": "evidence_grounding",
            "intent": "measure grounded extraction with abstention support",
            "messages": [{"role": "user", "content": "x"}],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 64,
                "response_format": "json_object",
                "reasoning_mode": "ignore",
            },
            "output_contract": {
                "id": "strict_json_v2",
                "canonicalizer": "strict_json_v2",
            },
            "extractors": {
                "answer": extractor,
                "score": score_extractor,
            },
            "evaluation": {
                "reference": {
                    "expected_values": {"owner": "Alice Wong"},
                }
            },
            "required_capabilities": ["chat_completions", "json_object_response"],
            "weight_hint": 0.8,
            "tags": [],
            "risk_level": "low",
        }
    )


def test_registry_resolves_extractor_from_prompt_definition() -> None:
    registry = ExtractorRegistry.from_directory(
        ROOT / "extractors",
        handlers={"style_brief_v1": lambda text: {"char_len": len(text)}},
    )

    resolved = registry.get_for_prompt(build_prompt("style_brief_v1"))

    assert resolved.descriptor.name == "style_brief_v1"


def test_registry_rejects_unknown_extractor_names() -> None:
    registry = ExtractorRegistry.from_directory(ROOT / "extractors", handlers={})

    with pytest.raises(ExtractorValidationError):
        registry.get("unknown_family_v9")


def test_registry_enforces_json_serializable_feature_maps() -> None:
    registry = ExtractorRegistry.from_directory(
        ROOT / "extractors",
        handlers={"style_brief_v1": lambda text: {"bad": {1, 2}}},
    )

    with pytest.raises(ExtractorValidationError):
        registry.extract_answer(
            build_prompt("style_brief_v1"),
            CanonicalizedOutput(format_id="plain_text_v2", payload={"text": "example"}),
        )


def test_registry_extracts_score_features_from_prompt_context() -> None:
    registry = ExtractorRegistry(
        descriptors={
            "evidence_grounding_score_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "evidence_grounding_score_v1",
                    "family": "evidence_grounding",
                    "version": 1,
                    "features": ["value_accuracy"],
                }
            )
        },
        handlers={},
        score_handlers={
            "evidence_grounding_score_v1": lambda prompt, canonical_output: {
                "value_accuracy": 1.0
                if canonical_output.payload["task_result"]["owner"]
                == prompt.evaluation.reference["expected_values"]["owner"]
                else 0.0
            }
        },
    )

    feature_map = registry.extract_score(
        build_prompt(
            "evidence_grounding_v1",
            score_extractor="evidence_grounding_score_v1",
        ),
        CanonicalizedOutput(
            format_id="strict_json_v2",
            payload={"task_result": {"owner": "Alice Wong"}},
        ),
    )

    assert feature_map["value_accuracy"] == 1.0
