from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.comparator import compare_run
from modelfingerprint.services.profile_builder import build_profile

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "calibration_runs"


def load_run(name: str) -> RunArtifact:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return RunArtifact.model_validate(payload)


def test_comparator_ranks_profiles_and_computes_claimed_similarity() -> None:
    gpt_runs = [load_run("gpt_run1.json"), load_run("gpt_run2.json")]
    claude_runs = [load_run("claude_run1.json"), load_run("claude_run2.json")]
    profiles = [
        build_profile("gpt-5.3", gpt_runs, prompt_weights={"p001": 0.8}),
        build_profile("claude-ops-4.6", claude_runs, prompt_weights={"p001": 0.8}),
    ]
    target = RunArtifact.model_validate(
        {
            "run_id": "suspect-a.fingerprint-suite-v1",
            "suite_id": "fingerprint-suite-v1",
            "target_label": "suspect-a",
            "claimed_model": "gpt-5.3",
            "prompts": [
                {
                    "prompt_id": "p001",
                    "raw_output": "suspect sample",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "total_tokens": 15,
                    },
                    "features": {
                        "char_len": 41,
                        "uses_numbered_list": True,
                        "abstraction_level": "concrete",
                    },
                }
            ],
        }
    )

    result = compare_run(target, profiles)

    assert result.top1_model == "gpt-5.3"
    assert result.top2_model == "claude-ops-4.6"
    assert result.top1_similarity > result.top2_similarity
    assert result.claimed_model_similarity == result.top1_similarity
    assert result.margin > 0.0
    assert result.consistency == 1.0
