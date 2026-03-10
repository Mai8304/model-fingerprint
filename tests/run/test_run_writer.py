from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.run_writer import RunWriter
from modelfingerprint.settings import RepositoryPaths


def test_run_writer_persists_run_artifacts_under_date_directory(tmp_path: Path) -> None:
    writer = RunWriter(RepositoryPaths(root=tmp_path))
    artifact = RunArtifact.model_validate(
        {
            "run_id": "suspect-a.fingerprint-suite-v3",
            "suite_id": "fingerprint-suite-v3",
            "target_label": "suspect-a",
            "claimed_model": "gpt-5.3",
            "prompts": [
                {
                    "prompt_id": "p001",
                    "raw_output": "Use CRUD first. Event sourcing adds overhead.",
                    "usage": {
                        "input_tokens": 12,
                        "output_tokens": 8,
                        "total_tokens": 20,
                    },
                    "features": {
                        "char_len": 45,
                        "sentence_count": 2,
                    },
                }
            ],
        }
    )

    path = writer.write(artifact, run_date=date(2026, 3, 9))

    assert path == tmp_path / "runs" / "2026-03-09" / "suspect-a.fingerprint-suite-v3.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["prompts"][0]["raw_output"] == "Use CRUD first. Event sourcing adds overhead."
    assert payload["prompts"][0]["usage"]["total_tokens"] == 20
    assert payload["prompts"][0]["features"]["char_len"] == 45
