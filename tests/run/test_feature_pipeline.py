from __future__ import annotations

from pathlib import Path

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import UsageMetadata
from modelfingerprint.extractors.registry import build_default_registry
from modelfingerprint.services.feature_pipeline import FeaturePipeline, PromptExecutionResult

ROOT = Path(__file__).resolve().parents[2]


def build_prompt(prompt_id: str, family: str, extractor: str, output_type: str) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": prompt_id,
            "name": prompt_id,
            "family": family,
            "intent": "test",
            "template": "test",
            "variables": [],
            "output_contract": {"type": output_type},
            "extractor": extractor,
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
        run_id="suspect-a.default-v1",
        suite_id="default-v1",
        target_label="suspect-a",
        claimed_model="gpt-5.3",
        executions=executions,
    )

    assert artifact.prompts[0].raw_output == "Use CRUD first. Event sourcing adds overhead."
    assert artifact.prompts[0].usage.total_tokens == 20
    assert artifact.prompts[0].features["char_len"] == 45
    assert artifact.prompts[1].features["valid_format"] is True
