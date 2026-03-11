from __future__ import annotations

from pathlib import Path

import pytest

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import ExtractorDescriptor, ExtractorValidationError
from modelfingerprint.extractors.registry import ExtractorRegistry, build_default_registry

ROOT = Path(__file__).resolve().parents[2]


def build_prompt(extractor: str, score_extractor: str | None = None) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p021",
            "name": "evidence_bound_identity_resolution",
            "family": "evidence_grounding",
            "intent": "measure grounded extraction with abstention support",
            "messages": [{"role": "user", "content": "x"}],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 64,
                "response_format": "text",
                "reasoning_mode": "ignore",
            },
            "output_contract": {
                "id": "tolerant_json_v3",
                "canonicalizer": "tolerant_json_v3",
            },
            "extractors": {
                "answer": extractor,
                "score": score_extractor,
            },
            "evaluation": {
                "reference": {
                    "expected_task_result": {"owner": "Alice Wong"},
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
        handlers={"evidence_grounding_v3": lambda payload: {"char_len": len(payload.payload)}},
    )

    resolved = registry.get_for_prompt(build_prompt("evidence_grounding_v3"))

    assert resolved.descriptor.name == "evidence_grounding_v3"


def test_registry_rejects_unknown_extractor_names() -> None:
    registry = ExtractorRegistry.from_directory(ROOT / "extractors", handlers={})

    with pytest.raises(ExtractorValidationError):
        registry.get("unknown_family_v9")


def test_registry_enforces_json_serializable_feature_maps() -> None:
    registry = ExtractorRegistry.from_directory(
        ROOT / "extractors",
        handlers={"evidence_grounding_v3": lambda payload: {"bad": {1, 2}}},
    )

    with pytest.raises(ExtractorValidationError):
        registry.extract_answer(
            build_prompt("evidence_grounding_v3"),
            CanonicalizedOutput(
                format_id="tolerant_json_v3",
                payload={
                    "task_result": {"owner": "Alice Wong"},
                    "evidence": {"owner": ["e1"]},
                    "unknowns": {},
                    "violations": [],
                },
            ),
        )


def test_registry_extracts_score_features_from_prompt_context() -> None:
    registry = ExtractorRegistry(
        descriptors={
            "evidence_grounding_score_v3": ExtractorDescriptor.model_validate(
                {
                    "name": "evidence_grounding_score_v3",
                    "family": "evidence_grounding",
                    "version": 3,
                    "features": ["value_accuracy"],
                }
            )
        },
        handlers={},
        score_handlers={
            "evidence_grounding_score_v3": lambda prompt, canonical_output: {
                "value_accuracy": 1.0
                if canonical_output.payload["task_result"]["owner"]
                == prompt.evaluation.reference["expected_task_result"]["owner"]
                else 0.0
            }
        },
    )

    feature_map = registry.extract_score(
        build_prompt(
            "evidence_grounding_v3",
            score_extractor="evidence_grounding_score_v3",
        ),
        CanonicalizedOutput(
            format_id="tolerant_json_v3",
            payload={"task_result": {"owner": "Alice Wong"}},
        ),
    )

    assert feature_map["value_accuracy"] == 1.0


def test_default_registry_loads_shared_auxiliary_extractors() -> None:
    registry = build_default_registry(ROOT / "extractors")

    assert registry.has("reasoning_trace_v1")
    assert registry.has("completion_metadata_v1")
    assert registry.has("surface_contract_v1")
