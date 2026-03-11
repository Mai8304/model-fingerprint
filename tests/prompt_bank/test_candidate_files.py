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

    assert len(prompts) == 5
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

    v3_prompt_ids = ["p021", "p022", "p023", "p024", "p025"]
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
