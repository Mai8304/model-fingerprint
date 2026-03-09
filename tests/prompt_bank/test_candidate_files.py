from __future__ import annotations

from pathlib import Path

from modelfingerprint.services.prompt_bank import (
    FINGERPRINT_SUITE_ID,
    QUICK_CHECK_SUITE_ID,
    load_candidate_prompts,
    load_suites,
    validate_suite_references,
    validate_suite_subset,
)

ROOT = Path(__file__).resolve().parents[2]


def test_candidate_files_validate_and_reference_known_extractors() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")

    assert len(prompts) == 10
    assert {prompt.family for prompt in prompts.values()} == {
        "style_brief",
        "strict_format",
        "minimal_diff",
        "structured_extraction",
        "retrieval",
    }
    assert all(prompt.messages for prompt in prompts.values())
    assert all(prompt.generation.max_output_tokens > 0 for prompt in prompts.values())
    assert all(prompt.output_contract.id for prompt in prompts.values())
    assert all(prompt.extractors.answer for prompt in prompts.values())
    assert all(prompt.required_capabilities for prompt in prompts.values())


def test_released_suites_reference_existing_candidate_prompts() -> None:
    prompts = load_candidate_prompts(ROOT / "prompt-bank" / "candidates")
    suites = load_suites(ROOT / "prompt-bank" / "suites")

    validate_suite_references(prompts, suites)
    validate_suite_subset(suites[FINGERPRINT_SUITE_ID], suites[QUICK_CHECK_SUITE_ID])
