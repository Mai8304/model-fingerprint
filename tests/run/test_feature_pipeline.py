from __future__ import annotations

from modelfingerprint.canonicalizers.registry import CanonicalizerRegistry
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import (
    CanonicalizationEvent,
    CanonicalizedOutput,
    NormalizedCompletion,
    UsageMetadata,
)
from modelfingerprint.extractors.base import ExtractorDescriptor
from modelfingerprint.extractors.registry import ExtractorRegistry
from modelfingerprint.services.feature_pipeline import FeaturePipeline, PromptExecutionResult


def build_prompt() -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p003",
            "name": "event_log_state_resolution",
            "family": "state_tracking",
            "intent": "measure state tracking and rule execution",
            "messages": [{"role": "user", "content": "Return JSON only."}],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 96,
                "response_format": "text",
                "reasoning_mode": "capture_if_available",
            },
            "output_contract": {"id": "strict_json_v2", "canonicalizer": "strict_json_v2"},
            "extractors": {
                "answer": "state_tracking_v1",
                "score": "state_tracking_score_v1",
                "reasoning": "reasoning_trace_v1",
                "transport": "completion_metadata_v1",
            },
            "evaluation": {
                "reference": {
                    "expected_final_state": {
                        "ticket_a": {"status": "closed", "owner": "ops"},
                    }
                }
            },
            "required_capabilities": ["chat_completions"],
            "weight_hint": 0.9,
            "tags": ["state", "rules", "v2"],
            "risk_level": "low",
        }
    )


def build_registry() -> ExtractorRegistry:
    return ExtractorRegistry(
        descriptors={
            "state_tracking_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "state_tracking_v1",
                    "family": "state_tracking",
                    "version": 1,
                    "features": ["resolved_object_count", "default_used"],
                }
            ),
            "state_tracking_score_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "state_tracking_score_v1",
                    "family": "state_tracking",
                    "version": 1,
                    "features": ["state_accuracy", "owner_accuracy"],
                }
            ),
            "reasoning_trace_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "reasoning_trace_v1",
                    "family": "state_tracking",
                    "version": 1,
                    "features": ["step_count"],
                }
            ),
            "completion_metadata_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "completion_metadata_v1",
                    "family": "state_tracking",
                    "version": 1,
                    "features": ["reasoning_tokens"],
                }
            ),
            "surface_contract_v1": ExtractorDescriptor.model_validate(
                {
                    "name": "surface_contract_v1",
                    "family": "state_tracking",
                    "version": 1,
                    "features": ["had_markdown_fence"],
                }
            ),
        },
        handlers={
            "state_tracking_v1": lambda canonical_output: {
                "resolved_object_count": len(canonical_output.payload["task_result"]),
                "default_used": "defaults_used" in canonical_output.payload,
            },
            "reasoning_trace_v1": lambda reasoning_text: {
                "step_count": reasoning_text.count("\n") + 1
            },
            "completion_metadata_v1": lambda completion: {
                "reasoning_tokens": completion.usage.reasoning_tokens
            },
            "surface_contract_v1": lambda surface_input: {
                "had_markdown_fence": surface_input.raw_output.strip().startswith("```")
            },
        },
        score_handlers={
            "state_tracking_score_v1": lambda prompt, canonical_output: {
                "state_accuracy": 1.0
                if canonical_output.payload["task_result"]["ticket_a"]["status"]
                == prompt.evaluation.reference["expected_final_state"]["ticket_a"]["status"]
                else 0.0,
                "owner_accuracy": 1.0
                if canonical_output.payload["task_result"]["ticket_a"]["owner"]
                == prompt.evaluation.reference["expected_final_state"]["ticket_a"]["owner"]
                else 0.0,
            }
        },
    )


def test_feature_pipeline_extracts_multi_channel_features_and_preserves_events() -> None:
    registry = build_registry()
    pipeline = FeaturePipeline(
        registry=registry,
        canonicalizers=CanonicalizerRegistry(
            {
                "strict_json_v2": lambda raw_output: (
                    CanonicalizedOutput(
                        format_id="strict_json_v2",
                        payload={
                            "task_result": {
                                "ticket_a": {
                                    "status": "closed",
                                    "owner": "ops",
                                }
                            }
                        },
                    ),
                    [CanonicalizationEvent(code="removed_fence", message="removed markdown fence")],
                )
            }
        ),
    )

    artifact = pipeline.build_run_artifact(
        run_id="suspect-a.fingerprint-suite-v1",
        suite_id="fingerprint-suite-v1",
        target_label="suspect-a",
        claimed_model=None,
        executions=[
            PromptExecutionResult(
                prompt=build_prompt(),
                raw_output='```json\n{"answer":"yes","confidence":"high"}\n```',
                usage=UsageMetadata(
                    input_tokens=12,
                    output_tokens=18,
                    reasoning_tokens=24,
                    total_tokens=54,
                ),
                completion=NormalizedCompletion(
                    answer_text='```json\n{"answer":"yes","confidence":"high"}\n```',
                    reasoning_text="1. inspect request\n2. answer in strict json",
                    reasoning_visible=True,
                    finish_reason="stop",
                    latency_ms=18342,
                    usage=UsageMetadata(
                        input_tokens=12,
                        output_tokens=18,
                        reasoning_tokens=24,
                        total_tokens=54,
                    ),
                ),
            )
        ],
    )

    prompt_result = artifact.prompts[0]
    assert prompt_result.canonical_output is not None
    assert prompt_result.canonical_output.payload["task_result"]["ticket_a"]["status"] == "closed"
    assert [event.code for event in prompt_result.canonicalization_events] == ["removed_fence"]
    assert prompt_result.features["score.state_accuracy"] == 1.0
    assert prompt_result.features["score.owner_accuracy"] == 1.0
    assert prompt_result.features["answer.resolved_object_count"] == 1
    assert prompt_result.features["reasoning.step_count"] == 2
    assert prompt_result.features["surface.had_markdown_fence"] is True
    assert prompt_result.features["transport.reasoning_tokens"] == 24
    assert artifact.answer_coverage_ratio == 1.0
    assert artifact.reasoning_coverage_ratio == 1.0
