from __future__ import annotations

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.http_defaults import DEFAULT_BROWSER_USER_AGENT


def build_prompt() -> PromptDefinition:
    return PromptDefinition.model_validate(
        {
            "id": "p003",
            "name": "fixed_json_triage",
            "family": "strict_format",
            "intent": "detect strict JSON obedience",
            "messages": [
                {
                    "role": "system",
                    "content": "Return only the requested JSON object.",
                },
                {
                    "role": "user",
                    "content": (
                        'Reply with JSON only using fields "answer" and "confidence" in that order.'
                    ),
                },
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
            "required_capabilities": ["chat_completions", "json_object_response"],
            "weight_hint": 0.9,
            "tags": ["format", "json"],
            "risk_level": "low",
        }
    )


def build_endpoint() -> EndpointProfile:
    return EndpointProfile.model_validate(
        {
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
    )


def test_openai_chat_adapter_builds_wire_request_without_mutating_semantic_values() -> None:
    adapter = OpenAIChatDialectAdapter()

    request = adapter.build_request(build_prompt(), build_endpoint(), api_key="test-key")

    assert request.url == "https://api.siliconflow.cn/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert request.headers["User-Agent"] == DEFAULT_BROWSER_USER_AGENT
    assert request.body["model"] == "Pro/zai-org/GLM-5"
    assert request.body["messages"][0]["role"] == "system"
    assert request.body["max_tokens"] == 96
    assert request.body["response_format"] == {"type": "json_object"}


def test_openai_chat_adapter_applies_static_body_and_attempt_overrides() -> None:
    adapter = OpenAIChatDialectAdapter()
    endpoint = EndpointProfile.model_validate(
        {
            **build_endpoint().model_dump(mode="json"),
            "request_mapping": {
                "output_token_cap_field": "max_tokens",
                "json_response_shape": {"type": "json_object"},
                "static_body": {
                    "provider": {"sort": "throughput"},
                    "reasoning": {"effort": "minimal", "exclude": False},
                },
            },
        }
    )

    request = adapter.build_request(
        build_prompt(),
        endpoint,
        api_key="test-key",
        output_token_cap=240,
        body_overrides={"reasoning": {"effort": "none", "exclude": True}},
    )

    assert request.body["max_tokens"] == 240
    assert request.body["provider"] == {"sort": "throughput"}
    assert request.body["reasoning"] == {"effort": "none", "exclude": True}


def test_openai_chat_adapter_parses_reasoning_and_usage_fields() -> None:
    adapter = OpenAIChatDialectAdapter()

    completion = adapter.parse_response(
        build_endpoint(),
        {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": '{"answer":"yes","confidence":"high"}',
                        "reasoning_content": "1. check the request\n2. answer in strict json",
                    },
                }
            ],
            "usage": {
                "prompt_tokens": 12,
                "completion_tokens": 18,
                "total_tokens": 54,
                "completion_tokens_details": {
                    "reasoning_tokens": 24,
                },
            },
        },
        latency_ms=18342,
        raw_response_path="traces/2026-03-09/run-1/p003.response.json",
    )

    assert completion.answer_text == '{"answer":"yes","confidence":"high"}'
    assert completion.reasoning_text == "1. check the request\n2. answer in strict json"
    assert completion.reasoning_visible is True
    assert completion.finish_reason == "stop"
    assert completion.latency_ms == 18342
    assert completion.usage.reasoning_tokens == 24


def test_openai_chat_adapter_adds_openrouter_headers_for_openrouter_base_url() -> None:
    adapter = OpenAIChatDialectAdapter()
    endpoint = EndpointProfile.model_validate(
        {
            **build_endpoint().model_dump(mode="json"),
            "base_url": "https://openrouter.ai/api/v1",
            "model": "moonshotai/kimi-k2.5",
        }
    )

    request = adapter.build_request(build_prompt(), endpoint, api_key="test-key")

    assert request.headers["HTTP-Referer"] == "https://codex.local"
    assert request.headers["X-Title"] == "Codex Model Fingerprint"


def test_openai_chat_adapter_omits_non_required_fields_for_text_prompt() -> None:
    adapter = OpenAIChatDialectAdapter()
    prompt = build_prompt().model_copy(
        update={
            "generation": build_prompt().generation.model_copy(
                update={"response_format": "text"}
            )
        }
    )
    endpoint = EndpointProfile.model_validate(
        {
            **build_endpoint().model_dump(mode="json"),
            "base_url": "https://openrouter.ai/api/v1",
            "model": "anthropic/claude-opus-4.6",
        }
    )

    request = adapter.build_request(prompt, endpoint, api_key="test-key")

    assert sorted(request.body) == ["max_tokens", "messages", "model", "temperature", "top_p"]
    assert "response_format" not in request.body
    assert sorted(request.headers) == [
        "Accept",
        "Authorization",
        "Content-Type",
        "HTTP-Referer",
        "User-Agent",
        "X-Title",
    ]
