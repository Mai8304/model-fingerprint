from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

from modelfingerprint.webapi import bridge_cli
from modelfingerprint.webapi.contracts import WebRunInput, WebRunRecord

ROOT = Path(__file__).resolve().parents[2]


def test_bridge_cli_create_run_accepts_internal_run_id(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    class StubRunOrchestrator:
        def __init__(self, *, paths, store) -> None:
            captured["paths"] = paths
            captured["store"] = store

        def initialize_run(self, *, run_id: str, input: WebRunInput) -> WebRunRecord:
            captured["run_id"] = run_id
            captured["input"] = input
            return WebRunRecord(
                run_id=run_id,
                run_status="validating",
                result_state=None,
                cancel_requested=False,
                created_at=datetime(2026, 3, 10, 15, 0, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 10, 15, 0, 0, tzinfo=UTC),
                input=input,
                prompts=[],
                eta_seconds=None,
                failure=None,
                result=None,
            )

    monkeypatch.setattr(bridge_cli, "RunOrchestrator", StubRunOrchestrator)
    monkeypatch.setattr(
        sys,
        "stdin",
        StringIO(
            json.dumps(
                {
                    "run_id": "run_123",
                    "base_url": "https://api.example.com/v1",
                    "model_name": "gpt-4o-mini",
                    "fingerprint_model_id": "glm-5",
                }
            )
        ),
    )

    exit_code = bridge_cli.main(["--root", str(ROOT), "create-run"])

    assert exit_code == 0
    assert captured["run_id"] == "run_123"
    assert captured["input"] == WebRunInput(
        base_url="https://api.example.com/v1",
        model_name="gpt-4o-mini",
        fingerprint_model_id="glm-5",
    )
    assert json.loads(capsys.readouterr().out) == {
        "cancel_requested": False,
        "result_state": None,
        "run_id": "run_123",
        "run_status": "validating",
    }
