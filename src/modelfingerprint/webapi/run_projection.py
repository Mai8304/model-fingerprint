from __future__ import annotations

from modelfingerprint.webapi.contracts import (
    WebRunProgressSnapshot,
    WebRunRecord,
    WebRunSnapshot,
)


def project_run_snapshot(record: WebRunRecord) -> WebRunSnapshot:
    completed_prompts = sum(1 for prompt in record.prompts if prompt.status == "completed")
    failed_prompts = sum(1 for prompt in record.prompts if prompt.status == "failed")
    current_prompt = next((prompt.prompt_id for prompt in record.prompts if prompt.status == "running"), None)

    return WebRunSnapshot(
        run_id=record.run_id,
        run_status=record.run_status,
        result_state=record.result_state,
        cancel_requested=record.cancel_requested,
        created_at=record.created_at,
        updated_at=record.updated_at,
        input=record.input,
        progress=WebRunProgressSnapshot(
            completed_prompts=completed_prompts,
            failed_prompts=failed_prompts,
            total_prompts=len(record.prompts),
            current_prompt_id=current_prompt,
            eta_seconds=record.eta_seconds,
        ),
        prompts=record.prompts,
        failure=record.failure,
    )
