from __future__ import annotations

import json
import re
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from modelfingerprint.storage.filesystem import ensure_directories
from modelfingerprint.webapi.contracts import (
    WebRunInput,
    WebRunPrompt,
    WebRunRecord,
    WebRunStage,
)

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")
DEFAULT_STAGE_IDS = (
    "config_validation",
    "endpoint_resolution",
    "capability_probe",
    "prompt_execution",
    "comparison",
)


class RunStore:
    def __init__(
        self,
        directory: Path,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._directory = directory
        self._now = now or (lambda: datetime.now(UTC))
        ensure_directories(self._directory)

    def create_run(
        self,
        *,
        run_id: str,
        input: WebRunInput,
        prompt_ids: list[str],
    ) -> WebRunRecord:
        timestamp = self._now()
        record = WebRunRecord(
            run_id=run_id,
            run_status="validating",
            created_at=timestamp,
            updated_at=timestamp,
            input=input,
            current_stage_id="config_validation",
            current_stage_message="waiting for worker execution",
            stages=[
                WebRunStage(
                    id=stage_id,
                    status="running" if stage_id == "config_validation" else "pending",
                    message=(
                        "waiting for worker execution"
                        if stage_id == "config_validation"
                        else None
                    ),
                    started_at=timestamp if stage_id == "config_validation" else None,
                )
                for stage_id in DEFAULT_STAGE_IDS
            ],
            prompts=[
                WebRunPrompt(prompt_id=prompt_id, status="pending")
                for prompt_id in prompt_ids
            ],
        )
        self._write(record)
        return record

    def get(self, run_id: str) -> WebRunRecord:
        payload = json.loads(self._path_for(run_id).read_text(encoding="utf-8"))
        return WebRunRecord.model_validate(payload)

    def save(self, record: WebRunRecord) -> WebRunRecord:
        updated = record.model_copy(update={"updated_at": self._now()})
        self._write(updated)
        return updated

    def update(
        self,
        run_id: str,
        transform: Callable[[WebRunRecord, datetime], WebRunRecord],
    ) -> WebRunRecord:
        timestamp = self._now()
        record = self.get(run_id)
        updated = transform(record, timestamp)
        updated = updated.model_copy(update={"updated_at": timestamp})
        self._write(updated)
        return updated

    def mark_cancel_requested(self, run_id: str) -> WebRunRecord:
        record = self.get(run_id)
        updated = record.model_copy(update={"cancel_requested": True, "updated_at": self._now()})
        self._write(updated)
        return updated

    def _write(self, record: WebRunRecord) -> None:
        self._path_for(record.run_id).write_text(
            json.dumps(record.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _path_for(self, run_id: str) -> Path:
        if not RUN_ID_PATTERN.fullmatch(run_id):
            raise ValueError(f"unsafe run_id: {run_id}")
        return self._directory / f"{run_id}.json"
