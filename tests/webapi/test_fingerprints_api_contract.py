from __future__ import annotations

import json
from pathlib import Path
from hashlib import sha256

from modelfingerprint.contracts.calibration import CalibrationArtifact
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
                            "prompt_id": "p041",
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


def _write_calibration(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = CalibrationArtifact.model_validate(
        {
            "suite_id": "fingerprint-suite-v32",
            "thresholds": {
                "match": 1.0,
                "suspicious": 0.95,
                "unknown": 0.9,
                "margin": 0.05,
                "consistency": 1.0,
            },
            "coverage_thresholds": {
                "answer_min": 1.0,
                "reasoning_min": 0.0,
            },
            "same_model_stats": {
                "mean": 1.0,
                "p05": 1.0,
                "p50": 1.0,
                "p95": 1.0,
            },
            "cross_model_stats": {
                "mean": 0.75,
                "p05": 0.7,
                "p50": 0.75,
                "p95": 0.8,
            },
            "protocol_expectations": {
                "satisfied": True,
                "required_capabilities": ["chat_completions"],
                "issues": [],
            },
        }
    )
    path.write_text(
        json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_prompt_bank(root: Path) -> None:
    candidates_dir = root / "prompt-bank" / "candidates"
    suites_dir = root / "prompt-bank" / "suites"
    candidates_dir.mkdir(parents=True, exist_ok=True)
    suites_dir.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)

    (suites_dir / "fingerprint-suite-v32.yaml").write_text(
        "\n".join(
            [
                "id: fingerprint-suite-v32",
                "name: Fingerprint Suite V32",
                "prompt_ids:",
                "  - p041",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (candidates_dir / "p041.yaml").write_text(
        "\n".join(
            [
                "id: p041",
                "name: Prompt p041",
                "family: boundary_decision",
                "intent: Validate structured extraction",
                "messages:",
                "  - role: system",
                "    content: Return JSON only.",
                "  - role: user",
                "    content: Solve p041.",
                "generation:",
                "  temperature: 0.0",
                "  top_p: 1.0",
                "  max_output_tokens: 64",
                "  response_format: text",
                "  reasoning_mode: ignore",
                "output_contract:",
                "  id: tolerant_json_v3",
                "  canonicalizer: tolerant_json_v3",
                "extractors:",
                "  answer: boundary_decision_v1",
                "  score: boundary_decision_score_v1",
                "  transport: completion_metadata_v1",
                "required_capabilities:",
                "  - chat_completions",
                "weight_hint: 1.0",
                "tags:",
                "  - registry-test",
                "risk_level: low",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_run(path: Path, model_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "run_id": f"{model_id}.fingerprint-suite-v32",
                "suite_id": "fingerprint-suite-v32",
                "target_label": model_id,
                "claimed_model": model_id,
                "prompt_count_total": 1,
                "prompt_count_completed": 1,
                "prompt_count_scoreable": 1,
                "answer_coverage_ratio": 1.0,
                "reasoning_coverage_ratio": 0.0,
                "prompts": [
                    {
                        "prompt_id": "p041",
                        "status": "completed",
                        "raw_output": "{\"answer\":\"ok\"}",
                        "usage": {
                            "input_tokens": 1,
                            "output_tokens": 1,
                            "reasoning_tokens": 0,
                            "total_tokens": 2,
                        },
                        "features": {"answer.char_len": 42},
                    }
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_manifest(root: Path, model_ids: list[str]) -> None:
    manifest_path = root / "calibration" / "fingerprint-suite-v32.manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "suite_id": "fingerprint-suite-v32",
        "suite_definition": {
            "path": "prompt-bank/suites/fingerprint-suite-v32.yaml",
            "sha256": sha256(
                (root / "prompt-bank" / "suites" / "fingerprint-suite-v32.yaml").read_bytes()
            ).hexdigest(),
            "prompt_ids": ["p041"],
        },
        "prompt_files": [
            {
                "prompt_id": "p041",
                "path": "prompt-bank/candidates/p041.yaml",
                "sha256": sha256(
                    (root / "prompt-bank" / "candidates" / "p041.yaml").read_bytes()
                ).hexdigest(),
            }
        ],
        "baseline_runs": [
            {
                "model_id": model_id,
                "path": f"runs/2026-03-17/{model_id}.fingerprint-suite-v32.json",
                "sha256": sha256(
                    (
                        root
                        / "runs"
                        / "2026-03-17"
                        / f"{model_id}.fingerprint-suite-v32.json"
                    ).read_bytes()
                ).hexdigest(),
            }
            for model_id in model_ids
        ],
        "profiles": [
            {
                "model_id": model_id,
                "path": f"profiles/fingerprint-suite-v32/{model_id}.json",
                "sha256": sha256(
                    (root / "profiles" / "fingerprint-suite-v32" / f"{model_id}.json").read_bytes()
                ).hexdigest(),
            }
            for model_id in model_ids
        ],
        "calibration": {
            "path": "calibration/fingerprint-suite-v32.json",
            "sha256": sha256(
                (root / "calibration" / "fingerprint-suite-v32.json").read_bytes()
            ).hexdigest(),
        },
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def test_list_fingerprint_models_returns_stable_v32_registry(tmp_path: Path) -> None:
    _write_prompt_bank(tmp_path)
    _write_profile(
        tmp_path / "profiles" / "fingerprint-suite-v32" / "gpt-4.1-mini.json",
        model_id="gpt-4.1-mini",
        suite_id="fingerprint-suite-v32",
    )
    _write_profile(
        tmp_path / "profiles" / "fingerprint-suite-v32" / "deepseek-chat.json",
        model_id="deepseek-chat",
        suite_id="fingerprint-suite-v32",
    )
    _write_profile(
        tmp_path / "profiles" / "fingerprint-suite-v32" / "glm-5.json",
        model_id="glm-5",
        suite_id="fingerprint-suite-v32",
    )
    _write_run(
        tmp_path / "runs" / "2026-03-17" / "gpt-4.1-mini.fingerprint-suite-v32.json",
        "gpt-4.1-mini",
    )
    _write_run(
        tmp_path / "runs" / "2026-03-17" / "deepseek-chat.fingerprint-suite-v32.json",
        "deepseek-chat",
    )
    _write_run(
        tmp_path / "runs" / "2026-03-17" / "glm-5.fingerprint-suite-v32.json",
        "glm-5",
    )
    _write_calibration(tmp_path / "calibration" / "fingerprint-suite-v32.json")
    _write_manifest(tmp_path, ["gpt-4.1-mini", "deepseek-chat", "glm-5"])

    items = list_fingerprint_models(RepositoryPaths(root=tmp_path))

    assert [item.model_dump(mode="json") for item in items] == [
        {
            "id": "deepseek-chat",
            "label": "DeepSeek Chat",
            "suite_id": "fingerprint-suite-v32",
            "available": True,
            "image_generation": None,
            "vision_understanding": None,
        },
        {
            "id": "glm-5",
            "label": "GLM-5",
            "suite_id": "fingerprint-suite-v32",
            "available": True,
            "image_generation": None,
            "vision_understanding": None,
        },
        {
            "id": "gpt-4.1-mini",
            "label": "GPT-4.1 Mini",
            "suite_id": "fingerprint-suite-v32",
            "available": True,
            "image_generation": None,
            "vision_understanding": None,
        },
    ]
