from __future__ import annotations

from pathlib import Path

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import UsageMetadata
from modelfingerprint.extractors.registry import build_default_registry
from modelfingerprint.services.feature_pipeline import FeaturePipeline, PromptExecutionResult

ROOT = Path(__file__).resolve().parents[2]


def build_prompt(prompt_id: str, family: str, extractor: str, output_type: str) -> PromptDefinition:
    output_contracts = {
        "plain_text": ("plain_text_v2", "plain_text_v2"),
        "json": ("strict_json_v2", "strict_json_v2"),
    }
    contract_id, canonicalizer = output_contracts[output_type]
    return PromptDefinition.model_validate(
        {
            "id": prompt_id,
            "name": prompt_id,
            "family": family,
            "intent": "test",
            "messages": [{"role": "user", "content": "test"}],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 64,
                "response_format": "text" if output_type == "plain_text" else "json_object",
                "reasoning_mode": "ignore",
            },
            "output_contract": {
                "id": contract_id,
                "canonicalizer": canonicalizer,
            },
            "extractors": {"answer": extractor},
            "required_capabilities": ["chat_completions"],
            "weight_hint": 0.5,
            "tags": [],
            "risk_level": "low",
        }
    )


def test_feature_pipeline_builds_run_artifact_with_features() -> None:
    registry = build_default_registry(ROOT / "extractors")
    pipeline = FeaturePipeline(registry)
    executions = [
        PromptExecutionResult(
            prompt=build_prompt("p001", "style_brief", "style_brief_v1", "plain_text"),
            raw_output="Use CRUD first. Event sourcing adds overhead.",
            usage=UsageMetadata(input_tokens=12, output_tokens=8, total_tokens=20),
        ),
        PromptExecutionResult(
            prompt=build_prompt("p003", "strict_format", "strict_format_v1", "json"),
            raw_output='{"answer":"yes","confidence":"high"}',
            usage=UsageMetadata(input_tokens=10, output_tokens=6, total_tokens=16),
        ),
    ]

    artifact = pipeline.build_run_artifact(
        run_id="suspect-a.fingerprint-suite-v1",
        suite_id="fingerprint-suite-v1",
        target_label="suspect-a",
        claimed_model="gpt-5.3",
        executions=executions,
    )

    assert artifact.prompts[0].raw_output == "Use CRUD first. Event sourcing adds overhead."
    assert artifact.prompts[0].usage is not None
    assert artifact.prompts[0].usage.total_tokens == 20
    assert artifact.prompts[0].features["char_len"] == 45
    assert artifact.prompt_count_total == 2
    assert artifact.prompt_count_completed == 2
    assert artifact.prompt_count_scoreable == 2
    assert artifact.answer_coverage_ratio == 1.0
    assert artifact.reasoning_coverage_ratio == 0.0
    assert artifact.prompts[1].features["valid_format"] is True
