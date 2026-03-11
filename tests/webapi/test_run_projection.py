from __future__ import annotations

from datetime import UTC, datetime

from modelfingerprint.webapi.contracts import (
    WebRunFailure,
    WebRunInput,
    WebRunPrompt,
    WebRunRecord,
    WebRunStage,
)
from modelfingerprint.webapi.run_projection import project_run_snapshot


def test_project_run_snapshot_derives_progress_from_prompt_state() -> None:
    record = WebRunRecord(
        run_id="run_001",
        run_status="running",
        result_state=None,
        cancel_requested=False,
        created_at=datetime(2026, 3, 10, 6, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 10, 6, 2, 0, tzinfo=UTC),
        input=WebRunInput(
            base_url="https://api.example.com/v1",
            model_name="gpt-4o-mini",
            fingerprint_model_id="glm-5",
        ),
        current_stage_id="prompt_execution",
        current_stage_message="running p003 (3/3)",
        stages=[
            WebRunStage(
                id="config_validation",
                status="completed",
                started_at=datetime(2026, 3, 10, 6, 0, 0, tzinfo=UTC),
                finished_at=datetime(2026, 3, 10, 6, 0, 1, tzinfo=UTC),
            ),
            WebRunStage(
                id="prompt_execution",
                status="running",
                message="running p003 (3/3)",
                started_at=datetime(2026, 3, 10, 6, 1, 0, tzinfo=UTC),
            ),
        ],
        prompts=[
            WebRunPrompt(prompt_id="p001", status="completed", elapsed_seconds=56),
            WebRunPrompt(
                prompt_id="p002",
                status="failed",
                elapsed_seconds=60,
                error_code="RESPONSE_TIMEOUT",
                http_status=504,
            ),
            WebRunPrompt(prompt_id="p003", status="running"),
        ],
        eta_seconds=360,
        failure=WebRunFailure(code="RESPONSE_TIMEOUT", message="upstream timed out"),
    )

    snapshot = project_run_snapshot(record)

    assert snapshot.progress.completed_prompts == 1
    assert snapshot.progress.failed_prompts == 1
    assert snapshot.progress.total_prompts == 3
    assert snapshot.progress.current_prompt_id == "p003"
    assert snapshot.progress.current_prompt_index == 3
    assert snapshot.progress.eta_seconds == 360
    assert snapshot.current_stage_id == "prompt_execution"
    assert snapshot.current_stage_message == "running p003 (3/3)"
    assert snapshot.stages[1].status == "running"
    assert snapshot.prompts[1].error_code == "RESPONSE_TIMEOUT"
    assert snapshot.failure is not None
    assert snapshot.failure.code == "RESPONSE_TIMEOUT"
