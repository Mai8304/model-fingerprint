from __future__ import annotations

from typing import Any

from modelfingerprint.services.capability_probe import (
    CapabilityProbeOutcome,
    HttpProbeResponse,
    _failure_outcome,
    classify_image_outcome,
    classify_streaming_outcome,
    classify_thinking_outcome,
    classify_tools_outcome,
    probe_capabilities,
    probe_image,
    probe_streaming,
    probe_thinking,
    probe_tools,
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


def test_classify_image_outcome_detects_image_assets() -> None:
    payload = {
        "data": [
            {
                "url": "https://example.com/image.png",
            }
        ]
    }

    outcome = classify_image_outcome(payload)

    assert outcome.status == "supported"
    assert outcome.evidence.get("asset_field") == "url"


def test_classify_image_outcome_marks_missing_assets_as_ignored() -> None:
    payload = {"created": 123}

    outcome = classify_image_outcome(payload)

    assert outcome == CapabilityProbeOutcome(
        capability="image",
        status="accepted_but_ignored",
        detail="request succeeded but no image asset field was returned",
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


def test_probe_image_uses_minimal_image_body(monkeypatch) -> None:
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

    outcome = probe_image(
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


def test_failure_outcome_treats_429_as_insufficient_evidence() -> None:
    outcome = _failure_outcome(
        status_code=429,
        latency_ms=250,
        detail='{"error":{"message":"rate limited"}}',
    )

    assert outcome.status == "insufficient_evidence"
    assert outcome.http_status == 429


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
        "modelfingerprint.services.capability_probe.probe_image",
        lambda **_: CapabilityProbeOutcome(capability="image", status="unsupported"),
    )

    payload = probe_capabilities(
        base_url="https://api.example.com/v1",
        api_key="secret",
        model="example-model",
    )

    assert payload["probe_mode"] == "minimal"
    assert payload["probe_version"] == "v1"
    assert payload["coverage_ratio"] == 0.75
