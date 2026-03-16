from __future__ import annotations

from pathlib import Path

from modelfingerprint.services.prompt_bank import (
    FINGERPRINT_SUITE_ID,
    QUICK_CHECK_SUITE_ID,
    load_candidate_prompts,
    load_suites,
    validate_release_suite_subsets,
    validate_suite_references,
    validate_suite_subset,
)

ROOT = Path(__file__).resolve().parents[2]


def test_candidate_files_validate_and_reference_known_extractors() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    assert len(prompts) == 15
    assert {prompt.family for prompt in prompts.values()} == {
        "evidence_grounding",
        "context_retrieval",
        "abstention",
        "state_tracking",
        "representation_alignment",
        "boundary_decision",
        "mention_classification",
        "selection_boundary",
    }
    assert all(prompt.messages for prompt in prompts.values())
    assert all(prompt.generation.max_output_tokens > 0 for prompt in prompts.values())
    assert all(prompt.output_contract.id for prompt in prompts.values())
    assert all(prompt.extractors.answer for prompt in prompts.values())
    assert all(prompt.required_capabilities for prompt in prompts.values())

    v3_prompt_ids = ["p021", "p022", "p023", "p024", "p025"]
    v31_prompt_ids = ["p031", "p032", "p033", "p034", "p035"]
    v32_prompt_ids = ["p041", "p042", "p043", "p044", "p045"]
    for prompt_id in v3_prompt_ids + v31_prompt_ids + v32_prompt_ids:
        prompt = prompts[prompt_id]
        assert prompt.output_contract.canonicalizer == "tolerant_json_v3"
        assert prompt.extractors.score is not None
        assert prompt.evaluation is not None
        assert prompt.evaluation.reference


def test_released_suites_reference_existing_candidate_prompts() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")
    suites = load_suites(ROOT / "prompt-bank" / "suites")

    validate_suite_references(prompts, suites)
    validate_suite_subset(suites[FINGERPRINT_SUITE_ID], suites[QUICK_CHECK_SUITE_ID])
    validate_release_suite_subsets(suites)


def test_v31_p032_uses_boundary_sensitive_retrieval_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p032"]
    assert prompt.name == "boundary_sensitive_context_retrieval_v31"
    assert "四个实体" in prompt.messages[-1].content
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference == {
        "expected_task_result": {
            "found_entities": ["Arbor", "Beacon", "Cinder", "Drift"],
            "excluded_entities": [
                "Arbor-review",
                "Harbor shadow",
                "Beacon Ops",
                "Project Cinder",
                "Drift-east",
            ],
        },
        "expected_evidence": {
            "paragraph_map": {
                "Arbor": "p1",
                "Beacon": "p2",
                "Cinder": "p2",
                "Drift": "p3",
            },
        },
    }


def test_v31_p033_uses_boundary_sensitive_abstention_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p033"]
    assert prompt.name == "boundary_sensitive_abstention_v31"
    assert "q4" in prompt.messages[-1].content
    assert "q5" not in prompt.messages[-1].content
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference == {
        "expected_task_result": {
            "q1": {"status": "answer", "value": "yes"},
            "q2": {"status": "unknown", "value": None},
            "q3": {"status": "answer", "value": "Mara Singh"},
            "q4": {"status": "conflict_unresolved", "value": None},
        }
    }


def test_v32_p044_uses_authority_boundary_matrix_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p044"]
    assert prompt.name == "authority_boundary_matrix_v32"
    assert "q1 到 q7" in prompt.messages[0].content
    assert "q7" in prompt.messages[-1].content
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference == {
        "expected_task_result": {
            "q1": {"s": "a", "v": "ops"},
            "q2": {"s": "a", "v": "no"},
            "q3": {"s": "a", "v": "no"},
            "q4": {"s": "a", "v": "override"},
            "q5": {"s": "a", "v": "yes"},
            "q6": {"s": "c", "v": None},
            "q7": {"s": "u", "v": None},
        }
    }


def test_v32_p045_uses_mention_threshold_classification_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p045"]
    assert prompt.name == "mention_threshold_classification_v32"
    assert "m1 到 m12" in prompt.messages[0].content
    assert "m12 staging-note" in prompt.messages[-1].content
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference == {
        "expected_task_result": {
            "m1": "C:openwhale_control",
            "m2": "C:openwhale_control",
            "m3": "C:atlas_db_east",
            "m4": "C:atlas_db_east",
            "m5": "M",
            "m6": "M",
            "m7": "M",
            "m8": "R",
            "m9": "R",
            "m10": "R",
            "m11": "R",
            "m12": "R",
        }
    }


def test_v32_p042_uses_retrieval_boundary_matrix_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p042"]
    assert prompt.name == "retrieval_boundary_matrix_v32"
    assert "允许的值只有 I、A、V、R" in prompt.messages[0].content
    assert "m10 Harbor shadow" in prompt.messages[-1].content
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference == {
        "expected_task_result": {
            "m1": "I",
            "m2": "R",
            "m3": "I",
            "m4": "R",
            "m5": "I",
            "m6": "R",
            "m7": "I",
            "m8": "V",
            "m9": "A",
            "m10": "V",
        }
    }


def test_v32_p041_uses_grounded_decision_matrix_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p041"]
    assert prompt.name == "grounded_decision_matrix_v32"
    assert prompt.family == "boundary_decision"
    assert "q1 到 q8" in prompt.messages[0].content
    assert "q8" in prompt.messages[-1].content
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference == {
        "expected_task_result": {
            "q1": {"s": "a", "v": "Elena Park"},
            "q2": {"s": "a", "v": "no"},
            "q3": {"s": "a", "v": "no"},
            "q4": {"s": "a", "v": "Marco Ruiz"},
            "q5": {"s": "u", "v": None},
            "q6": {"s": "a", "v": "no"},
            "q7": {"s": "a", "v": "2026-04-06 01:30 UTC"},
            "q8": {"s": "a", "v": "no"},
        }
    }
