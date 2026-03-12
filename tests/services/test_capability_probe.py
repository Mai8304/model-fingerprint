from __future__ import annotations

import http.client
from typing import Any

from modelfingerprint.services.capability_probe import (
    CapabilityProbeOutcome,
    HttpProbeResponse,
    _post_json,
    _default_headers,
    _failure_outcome,
    classify_image_generation_outcome,
    classify_streaming_outcome,
    classify_thinking_outcome,
    classify_tools_outcome,
    classify_vision_understanding_outcome,
    probe_capabilities,
    probe_image_generation,
    probe_streaming,
    probe_thinking,
    probe_tools,
    probe_vision_understanding,
)


def test_classify_thinking_outcome_detects_reasoning_tokens() -> None:
    payload = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {
            "completion_tokens_details": {
                "reasoning_tokens": 12,
            }
        },
    }

    outcome = classify_thinking_outcome(payload)

    assert outcome.status == "supported"
    assert "reasoning_tokens=12" in (outcome.detail or "")


def test_classify_tools_outcome_detects_tool_calls() -> None:
    payload = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "ping", "arguments": "{}"},
                        }
                    ]
                },
            }
        ]
    }

    outcome = classify_tools_outcome(payload)

    assert outcome.status == "supported"
    assert outcome.evidence.get("finish_reason") == "tool_calls"


def test_classify_streaming_outcome_detects_event_stream_chunks() -> None:
    body = b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n'

    outcome = classify_streaming_outcome(
        status_code=200,
        content_type="text/event-stream; charset=utf-8",
        body=body,
    )

    assert outcome.status == "supported"
    assert outcome.evidence.get("content_type") == "text/event-stream; charset=utf-8"


def test_classify_image_generation_outcome_detects_image_assets() -> None:
    payload = {
        "data": [
            {
                "url": "https://example.com/image.png",
            }
        ]
    }

    outcome = classify_image_generation_outcome(payload)

    assert outcome.status == "supported"
    assert outcome.evidence.get("asset_field") == "url"


def test_classify_image_generation_outcome_detects_openrouter_chat_image_assets() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "images": [
                        {
                            "image_url": {
                                "url": "https://example.com/generated.png",
                            }
                        }
                    ]
                }
            }
        ]
    }

    outcome = classify_image_generation_outcome(payload)

    assert outcome.status == "supported"
    assert outcome.evidence.get("asset_field") == "choices.0.message.images.0.image_url.url"


def test_classify_image_generation_outcome_marks_missing_assets_as_ignored() -> None:
    payload = {"created": 123}

    outcome = classify_image_generation_outcome(payload)

    assert outcome == CapabilityProbeOutcome(
        capability="image_generation",
        status="accepted_but_ignored",
        detail="request succeeded but no image asset field was returned",
        evidence={},
    )


def test_classify_vision_understanding_outcome_detects_red_square_answer() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": "红色",
                }
            }
        ]
    }

    outcome = classify_vision_understanding_outcome(payload)

    assert outcome.status == "supported"
    assert outcome.evidence.get("normalized_answer") == "red"


def test_classify_vision_understanding_outcome_marks_unrecognized_answers_as_ignored() -> None:
    payload = {
        "choices": [
            {
                "message": {
                    "content": "我不确定",
                }
            }
        ]
    }

    outcome = classify_vision_understanding_outcome(payload)

    assert outcome == CapabilityProbeOutcome(
        capability="vision_understanding",
        status="accepted_but_ignored",
        detail="request succeeded but no recognized grounded answer was returned",
        evidence={},
    )


def test_probe_thinking_sends_only_minimal_baseline_body(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        captured["url"] = url
        captured["headers"] = headers
        captured["body"] = body
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=b'{"choices":[{"message":{"reasoning":"ok","content":"ok"}}]}',
                latency_ms=12,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_thinking(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-model",
    )

    assert outcome.status == "supported"
    assert captured["body"] == {
        "model": "example-model",
        "messages": [{"role": "user", "content": "只返回 ok"}],
        "max_tokens": 32,
    }
    assert "User-Agent" in captured["headers"]


def test_probe_tools_adds_only_tools_delta(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        captured["body"] = body
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=(
                    b'{"choices":[{"finish_reason":"tool_calls","message":{"tool_calls":[{"id":"call_1","type":"function","function":{"name":"ping","arguments":"{}"}}]}}]}'
                ),
                latency_ms=12,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_tools(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-model",
    )

    assert outcome.status == "supported"
    assert captured["body"] == {
        "model": "example-model",
        "messages": [{"role": "user", "content": "调用 ping 工具，不要输出自然语言。"}],
        "max_tokens": 64,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "ping",
                    "description": "Return pong.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {"name": "ping"},
        },
    }


def test_probe_tools_retries_with_thinking_disabled_when_tool_choice_conflicts(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        calls.append(body)
        if len(calls) == 1:
            return (
                None,
                _failure_outcome(
                    status_code=400,
                    latency_ms=12,
                    detail=(
                        '{"error":{"message":"tool_choice \\"specified\\" is incompatible '
                        'with thinking enabled"}}'
                    ),
                ),
            )
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=(
                    b'{"choices":[{"finish_reason":"tool_calls","message":{"tool_calls":[{"id":"call_1","type":"function","function":{"name":"ping","arguments":"{}"}}]}}]}'
                ),
                latency_ms=18,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_tools(
        base_url="https://api.moonshot.ai/v1",
        api_key="secret",
        model="kimi-k2.5",
    )

    assert outcome.status == "supported"
    assert len(calls) == 2
    assert "thinking" not in calls[0]
    assert calls[1]["thinking"] == {"type": "disabled"}
    assert outcome.evidence.get("probe_path") == "thinking_disabled_retry"


def test_probe_streaming_adds_only_stream_delta(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        captured["body"] = body
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "text/event-stream; charset=utf-8"},
                body=b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\ndata: [DONE]\n\n',
                latency_ms=12,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_streaming(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-model",
    )

    assert outcome.status == "supported"
    assert captured["body"] == {
        "model": "example-model",
        "messages": [{"role": "user", "content": "只返回 ok"}],
        "max_tokens": 16,
        "stream": True,
    }


def test_probe_image_generation_uses_minimal_image_body(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        captured["url"] = url
        captured["body"] = body
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=b'{"data":[{"url":"https://example.com/image.png"}]}',
                latency_ms=12,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_image_generation(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-model",
    )

    assert outcome.status == "supported"
    assert captured["url"] == "https://api.example.com/v1/images/generations"
    assert captured["body"] == {
        "model": "example-model",
        "prompt": "a red square",
        "size": "256x256",
        "n": 1,
    }


def test_probe_image_generation_uses_chat_completions_for_openrouter_image_models(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        captured["url"] = url
        captured["body"] = body
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=(
                    b'{"choices":[{"message":{"images":[{"image_url":{"url":"https://example.com/generated.png"}}]}}]}'
                ),
                latency_ms=12,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_image_generation(
        base_url="https://openrouter.ai/api/v1",
        api_key="secret",
        model="google/gemini-2.5-flash-image",
    )

    assert outcome.status == "supported"
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["body"] == {
        "model": "google/gemini-2.5-flash-image",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Generate a 256x256 image of a red square.",
                    }
                ],
            }
        ],
        "modalities": ["image", "text"],
    }


def test_probe_vision_understanding_sends_image_input_and_checks_answer(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        captured["url"] = url
        captured["body"] = body
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=b'{"choices":[{"message":{"content":"red"}}]}',
                latency_ms=12,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_vision_understanding(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-vision-model",
    )

    assert outcome.status == "supported"
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["body"]["model"] == "example-vision-model"
    assert captured["body"]["max_tokens"] == 64
    message = captured["body"]["messages"][0]
    assert message["role"] == "user"
    content = message["content"]
    assert content[0] == {"type": "text", "text": "图里是什么颜色的方块？只回答颜色。"}
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("https://")


def test_probe_vision_understanding_retries_with_data_url_when_remote_image_is_ignored(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        calls.append(body)
        if len(calls) == 1:
            return (
                HttpProbeResponse(
                    status_code=200,
                    headers={"content-type": "application/json"},
                    body=(
                        b'{"choices":[{"finish_reason":"length","message":{"content":null}}]}'
                    ),
                    latency_ms=12,
                ),
                None,
            )
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body=b'{"choices":[{"message":{"content":"red"}}]}',
                latency_ms=18,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_vision_understanding(
        base_url="https://openrouter.ai/api/v1",
        api_key="secret",
        model="example-vision-model",
    )

    assert outcome.status == "supported"
    assert len(calls) == 2
    first_message = calls[0]["messages"][0]
    second_message = calls[1]["messages"][0]
    assert calls[0]["max_tokens"] == 64
    assert calls[1]["max_tokens"] == 256
    assert first_message["content"][1]["image_url"]["url"].startswith("https://")
    assert second_message["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_probe_vision_understanding_uses_remote_image_result_when_data_url_gateway_path_would_fail(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_post_json(
        *,
        url: str,
        headers: dict[str, str],
        body: dict[str, object],
        timeout_seconds: int = 90,
    ):
        calls.append(body)
        return (
            HttpProbeResponse(
                status_code=200,
                headers={"content-type": "application/json"},
                body='{"choices":[{"message":{"content":"红色"}}]}'.encode("utf-8"),
                latency_ms=12,
            ),
            None,
        )

    monkeypatch.setattr("modelfingerprint.services.capability_probe._post_json", fake_post_json)

    outcome = probe_vision_understanding(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-vision-model",
    )

    assert outcome.status == "supported"
    assert len(calls) == 1
    message = calls[0]["messages"][0]
    assert calls[0]["max_tokens"] == 64
    assert message["content"][1]["image_url"]["url"].startswith("https://")


def test_failure_outcome_treats_429_as_insufficient_evidence() -> None:
    outcome = _failure_outcome(
        status_code=429,
        latency_ms=250,
        detail='{"error":{"message":"rate limited"}}',
    )

    assert outcome.status == "insufficient_evidence"
    assert outcome.http_status == 429


def test_post_json_treats_remote_disconnect_as_insufficient_evidence(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):
        raise http.client.RemoteDisconnected("Remote end closed connection without response")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    response, failure = _post_json(
        url="https://api.example.com/v1/chat/completions",
        headers={"Authorization": "Bearer secret"},
        body={"model": "example-model"},
    )

    assert response is None
    assert failure is not None
    assert failure.status == "insufficient_evidence"
    assert "Remote end closed connection without response" in (failure.detail or "")


def test_probe_capabilities_returns_probe_metadata_and_coverage(monkeypatch) -> None:
    monkeypatch.setattr(
        "modelfingerprint.services.capability_probe.probe_thinking",
        lambda **_: CapabilityProbeOutcome(capability="thinking", status="supported"),
    )
    monkeypatch.setattr(
        "modelfingerprint.services.capability_probe.probe_tools",
        lambda **_: CapabilityProbeOutcome(capability="tools", status="supported"),
    )
    monkeypatch.setattr(
        "modelfingerprint.services.capability_probe.probe_streaming",
        lambda **_: CapabilityProbeOutcome(capability="streaming", status="insufficient_evidence"),
    )
    monkeypatch.setattr(
        "modelfingerprint.services.capability_probe.probe_image_generation",
        lambda **_: CapabilityProbeOutcome(capability="image_generation", status="unsupported"),
    )
    monkeypatch.setattr(
        "modelfingerprint.services.capability_probe.probe_vision_understanding",
        lambda **_: CapabilityProbeOutcome(
            capability="vision_understanding",
            status="supported",
        ),
    )

    payload = probe_capabilities(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-model",
    )

    assert payload["probe_mode"] == "minimal"
    assert payload["probe_version"] == "v2"
    assert payload["coverage_ratio"] == 0.8


def test_default_headers_include_browser_user_agent() -> None:
    headers = _default_headers("https://api.example.com/v1", "secret")

    assert headers["User-Agent"].startswith("Mozilla/5.0")
