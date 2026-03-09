from __future__ import annotations

from pathlib import Path

import pytest

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import ExtractorValidationError
from modelfingerprint.extractors.registry import ExtractorRegistry

ROOT = Path(__file__).resolve().parents[2]


def build_prompt(extractor: str) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p001",
            "name": "concise_architecture_tradeoff",
            "family": "style_brief",
            "intent": "distinguish compact trade-off framing",
            "messages": [{"role": "user", "content": "x"}],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 64,
                "response_format": "text",
                "reasoning_mode": "ignore",
            },
            "output_contract": {
                "id": "plain_text_v2",
                "canonicalizer": "plain_text_v2",
            },
            "extractors": {"answer": extractor},
            "required_capabilities": ["chat_completions"],
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
