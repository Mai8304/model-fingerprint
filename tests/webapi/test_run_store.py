from __future__ import annotations

from datetime import UTC, datetime

import pytest

from modelfingerprint.webapi.contracts import WebRunInput
from modelfingerprint.webapi.run_store import RunStore


def test_run_store_round_trips_and_marks_cancel_requested(tmp_path) -> None:
    timestamps = iter(
        [
            datetime(2026, 3, 10, 6, 0, 0, tzinfo=UTC),
            datetime(2026, 3, 10, 6, 1, 0, tzinfo=UTC),
        ]
    )
    store = RunStore(tmp_path / ".webapi" / "runs", now=lambda: next(timestamps))

    created = store.create_run(
        run_id="run_001",
        input=WebRunInput(
            base_url="https://api.example.com/v1",
            model_name="gpt-4o-mini",
            fingerprint_model_id="glm-5",
        ),
        prompt_ids=["p001", "p002", "p003"],
    )

    assert created.run_status == "validating"
    assert created.result_state is None
    assert created.cancel_requested is False
    assert [prompt.prompt_id for prompt in created.prompts] == ["p001", "p002", "p003"]
    assert all(prompt.status == "pending" for prompt in created.prompts)

    loaded = store.get("run_001")
    assert loaded == created

    cancelled = store.mark_cancel_requested("run_001")
    assert cancelled.cancel_requested is True
    assert cancelled.updated_at == datetime(2026, 3, 10, 6, 1, 0, tzinfo=UTC)


def test_run_store_rejects_unsafe_run_ids(tmp_path) -> None:
    store = RunStore(tmp_path / ".webapi" / "runs")

    with pytest.raises(ValueError, match="unsafe run_id"):
        store.get("../escape")
