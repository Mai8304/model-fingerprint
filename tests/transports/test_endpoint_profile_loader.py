from __future__ import annotations

from pathlib import Path

import pytest

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.services.endpoint_profiles import (
    EndpointProfileValidationError,
    ensure_endpoint_supports_prompt,
    load_endpoint_profiles,
)

ROOT = Path(__file__).resolve().parents[2]


def build_prompt(required_capabilities: list[str]) -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p003",
            "name": "fixed_json_triage",
            "family": "strict_format",
            "intent": "detect strict JSON obedience",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        'Reply with JSON only using fields "answer" and "confidence" in that order.'
                    ),
                }
            ],
            "generation": {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_output_tokens": 96,
                "response_format": "json_object",
                "reasoning_mode": "capture_if_available",
            },
            "output_contract": {"id": "strict_json_v2", "canonicalizer": "strict_json_v2"},
            "extractors": {
                "answer": "strict_format_v1",
                "reasoning": "reasoning_trace_v1",
                "transport": "completion_metadata_v1",
            },
            "required_capabilities": required_capabilities,
            "weight_hint": 0.9,
            "tags": ["format", "json"],
            "risk_level": "low",
        }
    )


def test_loader_reads_profiles_from_disk_and_indexes_by_id() -> None:
    profiles = load_endpoint_profiles(ROOT / "tests" / "fixtures" / "endpoint_profiles")

    assert list(profiles) == ["deepseek-openai-chat", "siliconflow-openai-chat"]
    assert profiles["siliconflow-openai-chat"].model == "Pro/zai-org/GLM-5"


def test_loader_rejects_unknown_dialects(tmp_path: Path) -> None:
    profiles_dir = tmp_path / "endpoint_profiles"
    profiles_dir.mkdir(parents=True)
    (profiles_dir / "bad.yaml").write_text(
        """
id: bad-endpoint
dialect: made_up_v9
base_url: https://api.example.com/v1
model: bad-model
auth:
  kind: bearer_env
  env_var: MODEL_FINGERPRINT_API_KEY
capabilities:
  exposes_reasoning_text: false
  supports_json_object_response: true
  supports_temperature: true
  supports_top_p: true
  supports_output_token_cap: true
request_mapping:
  output_token_cap_field: max_tokens
  json_response_shape:
    type: json_object
response_mapping:
  answer_text_path: choices.0.message.content
  finish_reason_path: choices.0.finish_reason
  usage_paths:
    prompt_tokens: usage.prompt_tokens
    output_tokens: usage.completion_tokens
    total_tokens: usage.total_tokens
timeout_policy:
  connect_seconds: 10
  read_seconds: 120
retry_policy:
  max_attempts: 3
  retryable_statuses: [408, 429, 500]
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(EndpointProfileValidationError):
        load_endpoint_profiles(profiles_dir)


def test_capability_validation_happens_before_live_request() -> None:
    profiles = load_endpoint_profiles(ROOT / "tests" / "fixtures" / "endpoint_profiles")

    ensure_endpoint_supports_prompt(
        profiles["deepseek-openai-chat"],
        build_prompt(["chat_completions", "json_object_response"]),
    )

    with pytest.raises(EndpointProfileValidationError):
        ensure_endpoint_supports_prompt(
            profiles["deepseek-openai-chat"],
            build_prompt(["chat_completions", "visible_reasoning"]),
        )
