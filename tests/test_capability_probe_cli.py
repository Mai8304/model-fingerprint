from __future__ import annotations

import json

from typer.testing import CliRunner

from modelfingerprint.cli import app

runner = CliRunner()


def test_probe_capabilities_command_prints_json(monkeypatch) -> None:
    def fake_probe_capabilities(*, base_url: str, api_key: str, model: str):
        return {
            "base_url": base_url,
            "model": model,
            "probe_mode": "minimal",
            "probe_version": "v1",
            "coverage_ratio": 1.0,
            "results": {
                "thinking": {
                    "capability": "thinking",
                    "status": "supported",
                    "detail": "reasoning_tokens=12",
                    "evidence": {"reasoning_tokens": 12},
                }
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
