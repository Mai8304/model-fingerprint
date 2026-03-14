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

    assert len(prompts) == 7
    assert {prompt.family for prompt in prompts.values()} == {
        "evidence_grounding",
        "context_retrieval",
        "abstention",
        "state_tracking",
        "representation_alignment",
    }
    assert all(prompt.messages for prompt in prompts.values())
    assert all(prompt.generation.max_output_tokens > 0 for prompt in prompts.values())
    assert all(prompt.output_contract.id for prompt in prompts.values())
    assert all(prompt.extractors.answer for prompt in prompts.values())
    assert all(prompt.required_capabilities for prompt in prompts.values())

    v3_prompt_ids = ["p021", "p022", "p023", "p024", "p025", "p026", "p027"]
    for prompt_id in v3_prompt_ids:
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


def test_v31_p022_uses_boundary_sensitive_retrieval_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p022"]
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
                "Ember",
                "Drift-east",
                "Beacon-legacy",
                "Project Cinder",
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


def test_v31_p023_uses_boundary_sensitive_abstention_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p023"]
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


def test_v31_p027_uses_short_merge_threshold_reference() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    prompt = prompts["p027"]
    assert prompt.name == "short_merge_threshold_alignment_v31"
    assert "必须放进 rejected_items" in prompt.messages[-1].content
    assert prompt.evaluation is not None
    assert prompt.evaluation.reference == {
        "expected_task_result": {
            "canonical_entities": ["openwhale_control", "atlas_db_east"],
            "alias_map": {
                "OpenWhale Control Plane": "openwhale_control",
                "OW Control": "openwhale_control",
                "Atlas East DB": "atlas_db_east",
                "atlas-db-east": "atlas_db_east",
            },
            "ambiguous_mentions": ["OW", "Atlas"],
            "rejected_items": [
                "Mercury",
                "Project Mercury",
                "mercury-cutover",
                "control",
                "staging-note",
            ],
        }
    }
