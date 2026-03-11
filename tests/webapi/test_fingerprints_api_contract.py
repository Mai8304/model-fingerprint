from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.webapi.fingerprints import list_fingerprint_models


def _write_profile(path: Path, model_id: str, suite_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            ProfileArtifact.model_validate(
                {
                    "model_id": model_id,
                    "suite_id": suite_id,
                    "sample_count": 1,
                    "prompts": [
                        {
                            "prompt_id": "p021",
                            "weight": 1.0,
                            "features": {
                                "answer.char_len": {
                                    "kind": "numeric",
                                    "median": 42.0,
                                    "mad": 2.0,
                                }
                            },
                        }
                    ],
                }
            ).model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_list_fingerprint_models_returns_stable_v3_registry(tmp_path: Path) -> None:
    _write_profile(
        tmp_path / "profiles" / "fingerprint-suite-v3" / "gpt-4.1-mini.json",
        model_id="gpt-4.1-mini",
        suite_id="fingerprint-suite-v3",
    )
    _write_profile(
        tmp_path / "profiles" / "fingerprint-suite-v3" / "deepseek-chat.json",
        model_id="deepseek-chat",
        suite_id="fingerprint-suite-v3",
    )
    _write_profile(
        tmp_path / "profiles" / "fingerprint-suite-v3" / "glm-5.json",
        model_id="glm-5",
        suite_id="fingerprint-suite-v3",
    )

    items = list_fingerprint_models(RepositoryPaths(root=tmp_path))

    assert [item.model_dump(mode="json") for item in items] == [
        {
            "id": "deepseek-chat",
            "label": "DeepSeek Chat",
            "suite_id": "fingerprint-suite-v3",
            "available": True,
        },
        {
            "id": "glm-5",
            "label": "GLM-5",
            "suite_id": "fingerprint-suite-v3",
            "available": True,
        },
        {
            "id": "gpt-4.1-mini",
            "label": "GPT-4.1 Mini",
            "suite_id": "fingerprint-suite-v3",
            "available": True,
        },
    ]
