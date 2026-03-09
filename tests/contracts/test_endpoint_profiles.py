from __future__ import annotations

import pytest
from pydantic import ValidationError

from modelfingerprint.contracts.endpoint import EndpointProfile


def test_endpoint_profile_parses_valid_payload() -> None:
    payload = {
        "id": "siliconflow-openai-chat",
        "dialect": "openai_chat_v1",
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "Pro/zai-org/GLM-5",
        "auth": {
            "kind": "bearer_env",
            "env_var": "MODEL_FINGERPRINT_API_KEY",
        },
        "capabilities": {
            "exposes_reasoning_text": True,
            "supports_json_object_response": True,
            "supports_temperature": True,
            "supports_top_p": True,
            "supports_output_token_cap": True,
        },
        "request_mapping": {
            "output_token_cap_field": "max_tokens",
            "json_response_shape": {"type": "json_object"},
        },
        "response_mapping": {
            "answer_text_path": "choices.0.message.content",
            "reasoning_text_path": "choices.0.message.reasoning_content",
            "finish_reason_path": "choices.0.finish_reason",
            "usage_paths": {
                "prompt_tokens": "usage.prompt_tokens",
                "output_tokens": "usage.completion_tokens",
                "total_tokens": "usage.total_tokens",
                "reasoning_tokens": "usage.completion_tokens_details.reasoning_tokens",
            },
        },
        "timeout_policy": {
            "connect_seconds": 10,
            "read_seconds": 120,
        },
        "retry_policy": {
            "max_attempts": 3,
            "retryable_statuses": [408, 429, 500, 502, 503, 504],
        },
    }

    profile = EndpointProfile.model_validate(payload)

    assert profile.dialect == "openai_chat_v1"
    assert profile.model == "Pro/zai-org/GLM-5"
    assert profile.capabilities.exposes_reasoning_text is True
    assert profile.response_mapping.reasoning_text_path == "choices.0.message.reasoning_content"


def test_endpoint_profile_rejects_impossible_capability_combinations() -> None:
    with pytest.raises(ValidationError):
        EndpointProfile.model_validate(
            {
                "id": "broken-openai-chat",
                "dialect": "openai_chat_v1",
                "base_url": "https://api.example.com/v1",
                "model": "broken-model",
                "auth": {
                    "kind": "bearer_env",
                    "env_var": "MODEL_FINGERPRINT_API_KEY",
                },
                "capabilities": {
                    "exposes_reasoning_text": True,
                    "supports_json_object_response": False,
                    "supports_temperature": True,
                    "supports_top_p": True,
                    "supports_output_token_cap": True,
                },
                "request_mapping": {
                    "output_token_cap_field": "max_tokens",
                    "json_response_shape": {"type": "json_object"},
                },
                "response_mapping": {
                    "answer_text_path": "choices.0.message.content",
                    "finish_reason_path": "choices.0.finish_reason",
                    "usage_paths": {
                        "prompt_tokens": "usage.prompt_tokens",
                        "output_tokens": "usage.completion_tokens",
                        "total_tokens": "usage.total_tokens",
                    },
                },
                "timeout_policy": {
                    "connect_seconds": 10,
                    "read_seconds": 120,
                },
                "retry_policy": {
                    "max_attempts": 3,
                    "retryable_statuses": [408, 429, 500],
                },
            }
        )
