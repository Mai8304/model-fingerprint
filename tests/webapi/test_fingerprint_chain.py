from __future__ import annotations

import hashlib
import json
from pathlib import Path

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.webapi.fingerprint_chain import (
    FingerprintChainError,
    load_web_fingerprint_chain,
)


def test_load_web_fingerprint_chain_accepts_only_manifest_pinned_v32_artifacts(
    tmp_path: Path,
) -> None:
    _write_prompt_bank(tmp_path)
    _write_profile(tmp_path, model_id="alpha-model")
    _write_profile(tmp_path, model_id="beta-model")
    _write_run(tmp_path, model_id="alpha-model")
    _write_run(tmp_path, model_id="beta-model")
    _write_calibration(tmp_path)
    _write_manifest(
        tmp_path,
        models=["alpha-model", "beta-model"],
    )

    chain = load_web_fingerprint_chain(RepositoryPaths(root=tmp_path))

    assert chain.suite.id == "fingerprint-suite-v32"
    assert chain.suite.prompt_ids == ["p041", "p042"]
    assert [profile.model_id for profile in chain.profiles] == ["alpha-model", "beta-model"]
    assert sorted(chain.baseline_runs) == ["alpha-model", "beta-model"]
    assert chain.calibration.thresholds.match == 1.0


def test_load_web_fingerprint_chain_rejects_prompt_hash_drift(tmp_path: Path) -> None:
    _write_prompt_bank(tmp_path)
    _write_profile(tmp_path, model_id="alpha-model")
    _write_run(tmp_path, model_id="alpha-model")
    _write_calibration(tmp_path)
    _write_manifest(
        tmp_path,
        models=["alpha-model"],
    )

    prompt_path = tmp_path / "prompt-bank" / "candidates" / "p041.yaml"
    prompt_path.write_text(prompt_path.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")

    try:
        load_web_fingerprint_chain(RepositoryPaths(root=tmp_path))
    except FingerprintChainError as exc:
        assert "sha256 mismatch" in str(exc)
        assert "p041.yaml" in str(exc)
    else:
        raise AssertionError("expected prompt hash drift to be rejected")


def test_load_web_fingerprint_chain_rejects_unpinned_profile_files(tmp_path: Path) -> None:
    _write_prompt_bank(tmp_path)
    _write_profile(tmp_path, model_id="alpha-model")
    _write_run(tmp_path, model_id="alpha-model")
    _write_calibration(tmp_path)
    _write_manifest(
        tmp_path,
        models=["alpha-model"],
    )
    _write_profile(tmp_path, model_id="stale-model")

    try:
        load_web_fingerprint_chain(RepositoryPaths(root=tmp_path))
    except FingerprintChainError as exc:
        assert "unexpected profile artifacts" in str(exc)
        assert "stale-model.json" in str(exc)
    else:
        raise AssertionError("expected stale profiles to be rejected")


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
                "  - p042",
                "",
            ]
        ),
        encoding="utf-8",
    )

    for prompt_id in ("p041", "p042"):
        (candidates_dir / f"{prompt_id}.yaml").write_text(
            "\n".join(
                [
                    f"id: {prompt_id}",
                    f"name: Prompt {prompt_id}",
                    "family: boundary_decision",
                    "intent: Validate structured extraction",
                    "messages:",
                    "  - role: system",
                    "    content: Return JSON only.",
                    "  - role: user",
                    f"    content: Solve {prompt_id}.",
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
                    "  - web-chain-test",
                    "risk_level: low",
                    "",
                ]
            ),
            encoding="utf-8",
        )


def _write_profile(root: Path, *, model_id: str) -> None:
    path = root / "profiles" / "fingerprint-suite-v32" / f"{model_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = ProfileArtifact.model_validate(
        {
            "model_id": model_id,
            "suite_id": "fingerprint-suite-v32",
            "sample_count": 1,
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 0.0,
            "prompts": [
                {
                    "prompt_id": "p041",
                    "weight": 1.0,
                    "answer_coverage_ratio": 1.0,
                    "reasoning_coverage_ratio": 0.0,
                    "expected_reasoning_visible": 0.0,
                    "features": {
                        "answer.label": {
                            "kind": "enum",
                            "distribution": {model_id: 1.0},
                        }
                    },
                },
                {
                    "prompt_id": "p042",
                    "weight": 1.0,
                    "answer_coverage_ratio": 1.0,
                    "reasoning_coverage_ratio": 0.0,
                    "expected_reasoning_visible": 0.0,
                    "features": {
                        "answer.label": {
                            "kind": "enum",
                            "distribution": {f"{model_id}-p042": 1.0},
                        }
                    },
                },
            ],
        }
    )
    path.write_text(
        json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_run(root: Path, *, model_id: str) -> None:
    path = root / "runs" / "2026-03-17" / f"{model_id}.fingerprint-suite-v32.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = RunArtifact.model_validate(
        {
            "run_id": f"{model_id}.fingerprint-suite-v32",
            "suite_id": "fingerprint-suite-v32",
            "target_label": model_id,
            "claimed_model": model_id,
            "prompt_count_total": 2,
            "prompt_count_completed": 2,
            "prompt_count_scoreable": 2,
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
                    "features": {"answer.label": model_id},
                },
                {
                    "prompt_id": "p042",
                    "status": "completed",
                    "raw_output": "{\"answer\":\"ok\"}",
                    "usage": {
                        "input_tokens": 1,
                        "output_tokens": 1,
                        "reasoning_tokens": 0,
                        "total_tokens": 2,
                    },
                    "features": {"answer.label": f"{model_id}-p042"},
                },
            ],
        }
    )
    path.write_text(
        json.dumps(payload.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_calibration(root: Path) -> None:
    path = root / "calibration" / "fingerprint-suite-v32.json"
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


def _write_manifest(root: Path, *, models: list[str]) -> None:
    path = root / "calibration" / "fingerprint-suite-v32.manifest.json"
    payload = {
        "suite_id": "fingerprint-suite-v32",
        "suite_definition": {
            "path": "prompt-bank/suites/fingerprint-suite-v32.yaml",
            "sha256": _sha256(root / "prompt-bank" / "suites" / "fingerprint-suite-v32.yaml"),
            "prompt_ids": ["p041", "p042"],
        },
        "prompt_files": [
            {
                "prompt_id": "p041",
                "path": "prompt-bank/candidates/p041.yaml",
                "sha256": _sha256(root / "prompt-bank" / "candidates" / "p041.yaml"),
            },
            {
                "prompt_id": "p042",
                "path": "prompt-bank/candidates/p042.yaml",
                "sha256": _sha256(root / "prompt-bank" / "candidates" / "p042.yaml"),
            },
        ],
        "baseline_runs": [
            {
                "model_id": model_id,
                "path": f"runs/2026-03-17/{model_id}.fingerprint-suite-v32.json",
                "sha256": _sha256(
                    root / "runs" / "2026-03-17" / f"{model_id}.fingerprint-suite-v32.json"
                ),
            }
            for model_id in models
        ],
        "profiles": [
            {
                "model_id": model_id,
                "path": f"profiles/fingerprint-suite-v32/{model_id}.json",
                "sha256": _sha256(
                    root / "profiles" / "fingerprint-suite-v32" / f"{model_id}.json"
                ),
            }
            for model_id in models
        ],
        "calibration": {
            "path": "calibration/fingerprint-suite-v32.json",
            "sha256": _sha256(root / "calibration" / "fingerprint-suite-v32.json"),
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
