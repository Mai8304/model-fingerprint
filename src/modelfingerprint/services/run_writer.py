from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.storage.filesystem import ensure_directories


class RunWriter:
    def __init__(self, paths: RepositoryPaths) -> None:
        self._paths = paths

    def write(self, artifact: RunArtifact, run_date: date) -> Path:
        validated = RunArtifact.model_validate(artifact.model_dump())
        output_dir = self._paths.runs_dir / run_date.isoformat()
        ensure_directories(output_dir)
        output_path = output_dir / f"{validated.run_id}.json"
        output_path.write_text(
            json.dumps(validated.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return output_path
