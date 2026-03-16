from __future__ import annotations

from pathlib import Path

import pytest

from modelfingerprint.services.prompt_bank import (
    FINGERPRINT_SUITE_ID,
    PromptBankValidationError,
    QUICK_CHECK_SUITE_ID,
    load_candidate_prompts,
    load_suites,
    validate_suite_subset,
)


def write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_load_candidate_prompts_from_disk(tmp_path: Path) -> None:
    candidates_dir = tmp_path / "prompt-bank" / "candidates"
    candidates_dir.mkdir(parents=True)
    write_yaml(
        candidates_dir / "p021.yaml",
        """
id: p021
name: grounded_owner_resolution
family: evidence_grounding
intent: distinguish grounded extraction under mixed evidence
messages:
  - role: user
    content: return a grounded owner and role result
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 120
  response_format: text
  reasoning_mode: capture_if_available
output_contract:
  id: tolerant_json_v3
  canonicalizer: tolerant_json_v3
extractors:
  answer: evidence_grounding_v3
  score: evidence_grounding_score_v3
  reasoning: reasoning_trace_v1
  transport: completion_metadata_v1
required_capabilities: [chat_completions]
weight_hint: 0.8
tags: [grounding]
risk_level: low
""".strip(),
    )
    write_yaml(
        candidates_dir / "p023.yaml",
        """
id: p023
name: tri_state_incident_resolution
family: abstention
intent: detect answer, unknown, and conflict resolution
messages:
  - role: system
    content: return only the requested JSON object
  - role: user
    content: produce a fixed JSON object
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 128
  response_format: text
  reasoning_mode: capture_if_available
output_contract:
  id: tolerant_json_v3
  canonicalizer: tolerant_json_v3
extractors:
  answer: abstention_v3
  score: abstention_score_v3
  reasoning: reasoning_trace_v1
  transport: completion_metadata_v1
required_capabilities: [chat_completions]
weight_hint: 0.6
tags: [abstention]
risk_level: low
""".strip(),
    )

    prompts = load_candidate_prompts(candidates_dir)

    assert list(prompts) == ["p021", "p023"]
    assert prompts["p021"].messages[0].role == "user"
    assert prompts["p021"].generation.max_output_tokens == 120
    assert prompts["p021"].output_contract.id == "tolerant_json_v3"
    assert prompts["p021"].extractors.answer == "evidence_grounding_v3"
    assert prompts["p023"].required_capabilities == ["chat_completions"]


def test_quick_check_suite_must_be_strict_subset_of_fingerprint_suite(tmp_path: Path) -> None:
    suites_dir = tmp_path / "prompt-bank" / "suites"
    write_yaml(
        suites_dir / "fingerprint-suite-v3.yaml",
        """
id: fingerprint-suite-v3
name: fingerprint suite v3
prompt_ids: [p021, p023, p024]
""".strip(),
    )
    write_yaml(
        suites_dir / "quick-check-v3.yaml",
        """
id: quick-check-v3
name: quick check v3
prompt_ids: [p021, p023]
""".strip(),
    )

    suites = load_suites(suites_dir)

    validate_suite_subset(suites["fingerprint-suite-v3"], suites["quick-check-v3"])


def test_repository_v3_suite_is_loadable_and_has_expected_prompt_ids() -> None:
    root = Path(__file__).resolve().parents[2]
    suites = load_suites(root / "prompt-bank" / "suites")

    assert FINGERPRINT_SUITE_ID == "fingerprint-suite-v32"
    assert QUICK_CHECK_SUITE_ID == "quick-check-v32"
    assert set(suites) == {
        "fingerprint-suite-v3",
        "quick-check-v3",
        "fingerprint-suite-v31",
        "quick-check-v31",
        "fingerprint-suite-v32",
        "quick-check-v32",
    }

    suite = suites["fingerprint-suite-v3"]
    quick_check = suites["quick-check-v3"]
    suite_v31 = suites["fingerprint-suite-v31"]
    quick_check_v31 = suites["quick-check-v31"]
    suite_v32 = suites["fingerprint-suite-v32"]
    quick_check_v32 = suites["quick-check-v32"]

    assert suite.prompt_ids == ["p021", "p022", "p023", "p024", "p025"]
    assert set(quick_check.prompt_ids) < set(suite.prompt_ids)
    assert suite_v31.prompt_ids == ["p031", "p032", "p033", "p034", "p035"]
    assert set(quick_check_v31.prompt_ids) < set(suite_v31.prompt_ids)
    assert suite_v32.prompt_ids == ["p041", "p042", "p043", "p044", "p045"]
    assert set(quick_check_v32.prompt_ids) < set(suite_v32.prompt_ids)


def test_duplicate_prompt_ids_and_unknown_extractors_are_rejected(
    tmp_path: Path,
) -> None:
    candidates_dir = tmp_path / "prompt-bank" / "candidates"
    candidates_dir.mkdir(parents=True)
    write_yaml(
        candidates_dir / "first.yaml",
        """
id: p021
name: one
family: evidence_grounding
intent: first
messages:
  - role: user
    content: first
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 120
  response_format: text
  reasoning_mode: ignore
output_contract:
  id: tolerant_json_v3
  canonicalizer: tolerant_json_v3
extractors:
  answer: evidence_grounding_v3
required_capabilities: [chat_completions]
weight_hint: 0.5
tags: []
risk_level: low
""".strip(),
    )
    write_yaml(
        candidates_dir / "second.yaml",
        """
id: p021
name: two
family: evidence_grounding
intent: second
messages:
  - role: user
    content: second
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 120
  response_format: text
  reasoning_mode: ignore
output_contract:
  id: tolerant_json_v3
  canonicalizer: tolerant_json_v3
extractors:
  answer: evidence_grounding_v3
required_capabilities: [chat_completions]
weight_hint: 0.5
tags: []
risk_level: low
""".strip(),
    )

    with pytest.raises(PromptBankValidationError):
        load_candidate_prompts(candidates_dir)

    write_yaml(
        candidates_dir / "second.yaml",
        """
id: p023
name: two
family: abstention
intent: second
messages:
  - role: user
    content: second
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 120
  response_format: text
  reasoning_mode: ignore
output_contract:
  id: tolerant_json_v3
  canonicalizer: tolerant_json_v3
extractors:
  answer: made_up_v9
required_capabilities: [chat_completions]
weight_hint: 0.5
tags: []
risk_level: low
""".strip(),
    )

    with pytest.raises(PromptBankValidationError):
        load_candidate_prompts(candidates_dir)


def test_prompt_definitions_require_messages_generation_and_capabilities(tmp_path: Path) -> None:
    candidates_dir = tmp_path / "prompt-bank" / "candidates"
    candidates_dir.mkdir(parents=True)
    write_yaml(
        candidates_dir / "p021.yaml",
        """
id: p021
name: broken
family: evidence_grounding
intent: missing generation and capabilities
messages:
  - role: user
    content: hello
output_contract:
  id: tolerant_json_v3
  canonicalizer: tolerant_json_v3
extractors:
  answer: evidence_grounding_v3
weight_hint: 0.5
tags: []
risk_level: low
""".strip(),
    )

    with pytest.raises(Exception):
        load_candidate_prompts(candidates_dir)
