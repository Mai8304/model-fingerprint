from __future__ import annotations

import json
from dataclasses import dataclass

import pytest
from typer.testing import CliRunner

from modelfingerprint.cli import app

runner = CliRunner()


def test_probe_capabilities_command_prints_json(monkeypatch) -> None:
    def fake_probe_capabilities(*, base_url: str, api_key: str, model: str):
        return {
            "base_url": base_url,
            "model": model,
            "probe_mode": "minimal",
            "probe_version": "v2",
            "coverage_ratio": 1.0,
            "results": {
                "thinking": {
                    "capability": "thinking",
                    "status": "supported",
                    "detail": "reasoning_tokens=12",
                    "evidence": {"reasoning_tokens": 12},
                },
                "image_generation": {
                    "capability": "image_generation",
                    "status": "supported",
                },
                "vision_understanding": {
                    "capability": "vision_understanding",
                    "status": "accepted_but_ignored",
                },
            },
        }

    monkeypatch.setattr(
        "modelfingerprint.cli.probe_capabilities",
        fake_probe_capabilities,
    )

    result = runner.invoke(
        app,
        [
            "probe-capabilities",
            "--base-url",
            "https://api.example.com/v1",
            "--api-key",
            "secret-key",
            "--model",
            "example-model",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["model"] == "example-model"
    assert payload["probe_mode"] == "minimal"
    assert payload["results"]["thinking"]["status"] == "supported"
    assert payload["results"]["image_generation"]["status"] == "supported"
    assert payload["results"]["vision_understanding"]["status"] == "accepted_but_ignored"


@dataclass(frozen=True)
class ProbeCliBaseline:
    base_url: str
    model: str
    payload: dict[str, object]


PROBE_CLI_BASELINES = [
    ProbeCliBaseline(
        base_url="https://openrouter.ai/api/v1",
        model="z-ai/glm-5",
        payload={
            "base_url": "https://openrouter.ai/api/v1",
            "model": "z-ai/glm-5",
            "probe_mode": "minimal",
            "probe_version": "v2",
            "coverage_ratio": 0.8,
            "results": {
                "thinking": {
                    "capability": "thinking",
                    "status": "supported",
                    "detail": "reasoning visible",
                    "evidence": {"field": "reasoning"},
                },
                "tools": {
                    "capability": "tools",
                    "status": "supported",
                    "detail": "tool call emitted",
                    "evidence": {"probe_path": "standard"},
                },
                "streaming": {
                    "capability": "streaming",
                    "status": "supported",
                    "detail": "sse",
                    "evidence": {"content_type": "text/event-stream"},
                },
                "image_generation": {
                    "capability": "image_generation",
                    "status": "unsupported",
                    "detail": "not available",
                    "evidence": {"http_status": 404},
                },
                "vision_understanding": {
                    "capability": "vision_understanding",
                    "status": "insufficient_evidence",
                    "detail": "not sampled in CLI smoke",
                    "evidence": {"http_status": 429},
                },
            },
        },
    ),
    ProbeCliBaseline(
        base_url="https://api.moonshot.ai/v1",
        model="kimi-k2.5",
        payload={
            "base_url": "https://api.moonshot.ai/v1",
            "model": "kimi-k2.5",
            "probe_mode": "minimal",
            "probe_version": "v2",
            "coverage_ratio": 1.0,
            "results": {
                "thinking": {
                    "capability": "thinking",
                    "status": "supported",
                    "detail": "reasoning_content visible",
                    "evidence": {"field": "reasoning_content"},
                },
                "tools": {
                    "capability": "tools",
                    "status": "supported",
                    "detail": "retry with thinking disabled",
                    "evidence": {"probe_path": "thinking_disabled_retry"},
                },
                "streaming": {
                    "capability": "streaming",
                    "status": "supported",
                    "detail": "sse",
                    "evidence": {"content_type": "text/event-stream"},
                },
                "image_generation": {
                    "capability": "image_generation",
                    "status": "unsupported",
                    "detail": "not available",
                    "evidence": {"http_status": 404},
                },
                "vision_understanding": {
                    "capability": "vision_understanding",
                    "status": "supported",
                    "detail": "data-url fallback",
                    "evidence": {"probe_path": "data_url_retry"},
                },
            },
        },
    ),
]


@pytest.mark.parametrize("baseline", PROBE_CLI_BASELINES)
def test_probe_capabilities_command_prints_protocol_smoke_baseline_json(
    monkeypatch,
    baseline: ProbeCliBaseline,
) -> None:
    def fake_probe_capabilities(*, base_url: str, api_key: str, model: str):
        assert base_url == baseline.base_url
        assert api_key == "secret-key"
        assert model == baseline.model
        return baseline.payload

    monkeypatch.setattr(
        "modelfingerprint.cli.probe_capabilities",
        fake_probe_capabilities,
    )

    result = runner.invoke(
        app,
        [
            "probe-capabilities",
            "--base-url",
            baseline.base_url,
            "--api-key",
            "secret-key",
            "--model",
            baseline.model,
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == baseline.payload
