from __future__ import annotations

import pytest

from modelfingerprint.canonicalizers.base import CanonicalizationError
from modelfingerprint.canonicalizers.registry import CanonicalizerRegistry
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizationEvent, CanonicalizedOutput


def build_prompt(canonicalizer: str) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p003",
            "name": "fixed_json_triage",
            "family": "strict_format",
            "intent": "detect strict JSON obedience",
            "messages": [{"role": "user", "content": "Return JSON only."}],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 96,
                "response_format": "json_object",
                "reasoning_mode": "ignore",
            },
            "output_contract": {
                "id": "strict_json_v2",
                "canonicalizer": canonicalizer,
            },
            "extractors": {"answer": "strict_format_v1"},
            "required_capabilities": ["chat_completions", "json_object_response"],
            "weight_hint": 0.9,
            "tags": ["format", "json"],
            "risk_level": "low",
        }
    )


def test_registry_resolves_prompt_canonicalizer_and_returns_events() -> None:
    registry = CanonicalizerRegistry(
        {
            "strict_json_v2": lambda raw_output: (
                CanonicalizedOutput(
                    format_id="strict_json_v2",
                    payload={"answer": "yes", "confidence": "high"},
                ),
                [CanonicalizationEvent(code="removed_fence", message="removed markdown fence")],
            )
        }
    )

    canonical_output, events = registry.canonicalize(
        build_prompt("strict_json_v2"),
        '```json\n{"answer":"yes","confidence":"high"}\n```',
    )

    assert canonical_output.format_id == "strict_json_v2"
    assert canonical_output.payload["answer"] == "yes"
    assert events[0].code == "removed_fence"


def test_registry_rejects_unknown_canonicalizers() -> None:
    registry = CanonicalizerRegistry({})

    with pytest.raises(CanonicalizationError, match="unknown canonicalizer"):
        registry.canonicalize(build_prompt("missing_v9"), '{"answer":"yes","confidence":"high"}')


def test_registry_surfaces_typed_canonicalization_errors() -> None:
    registry = CanonicalizerRegistry(
        {
            "strict_json_v2": lambda raw_output: (_ for _ in ()).throw(
                CanonicalizationError(
                    code="invalid_json",
                    message="response body is not valid JSON",
                )
            )
        }
    )

    with pytest.raises(CanonicalizationError) as exc_info:
        registry.canonicalize(build_prompt("strict_json_v2"), "not-json")

    assert exc_info.value.code == "invalid_json"


def test_registry_supports_tolerant_json_v3_handler() -> None:
    registry = CanonicalizerRegistry(
        {
            "tolerant_json_v3": lambda raw_output: (
                CanonicalizedOutput(
                    format_id="tolerant_json_v3",
                    payload={"task_result": {}, "evidence": {}, "unknowns": {}, "violations": []},
                ),
                [
                    CanonicalizationEvent(
                        code="stripped_prefix_text",
                        message="removed explanatory text before JSON object",
                    )
                ],
            )
        }
    )

    canonical_output, events = registry.canonicalize(
        build_prompt("tolerant_json_v3"),
        '结果如下：{"task_result":{},"evidence":{},"unknowns":{},"violations":[]}',
    )

    assert canonical_output.format_id == "tolerant_json_v3"
    assert events[0].code == "stripped_prefix_text"
