from __future__ import annotations

from pathlib import Path

import pytest

from modelfingerprint.services.prompt_bank import (
    PromptBankValidationError,
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
        candidates_dir / "p001.yaml",
        """
id: p001
name: concise_architecture_tradeoff
family: style_brief
intent: distinguish compact trade-off framing
messages:
  - role: user
    content: explain why event sourcing is not always the default
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 120
  response_format: text
  reasoning_mode: capture_if_available
output_contract:
  id: plain_text_v2
  canonicalizer: plain_text_v2
extractors:
  answer: style_brief_v1
  reasoning: reasoning_trace_v1
  transport: completion_metadata_v1
required_capabilities: [chat_completions]
weight_hint: 0.8
tags: [style]
risk_level: low
""".strip(),
    )
    write_yaml(
        candidates_dir / "p002.yaml",
        """
id: p002
name: fixed_json_summary
family: strict_format
intent: detect strict format obedience
messages:
  - role: system
    content: return only the requested JSON object
  - role: user
    content: produce a fixed JSON object
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 128
  response_format: json_object
  reasoning_mode: ignore
output_contract:
  id: strict_json_v2
  canonicalizer: strict_json_v2
extractors:
  answer: strict_format_v1
required_capabilities: [chat_completions, json_object_response]
weight_hint: 0.6
tags: [format]
risk_level: low
""".strip(),
    )

    prompts = load_candidate_prompts(candidates_dir)

    assert list(prompts) == ["p001", "p002"]
    assert prompts["p001"].messages[0].role == "user"
    assert prompts["p001"].generation.max_output_tokens == 120
    assert prompts["p001"].output_contract.id == "plain_text_v2"
    assert prompts["p001"].extractors.answer == "style_brief_v1"
    assert prompts["p002"].required_capabilities == ["chat_completions", "json_object_response"]


def test_quick_check_suite_must_be_strict_subset_of_fingerprint_suite(tmp_path: Path) -> None:
    suites_dir = tmp_path / "prompt-bank" / "suites"
    write_yaml(
        suites_dir / "fingerprint-suite-v1.yaml",
        """
id: fingerprint-suite-v1
name: fingerprint suite v1
prompt_ids: [p001, p002, p003]
""".strip(),
    )
    write_yaml(
        suites_dir / "quick-check-v1.yaml",
        """
id: quick-check-v1
name: quick check v1
prompt_ids: [p001, p002]
""".strip(),
    )

    suites = load_suites(suites_dir)

    validate_suite_subset(suites["fingerprint-suite-v1"], suites["quick-check-v1"])


def test_duplicate_prompt_ids_and_unknown_extractors_are_rejected(
    tmp_path: Path,
) -> None:
    candidates_dir = tmp_path / "prompt-bank" / "candidates"
    candidates_dir.mkdir(parents=True)
    write_yaml(
        candidates_dir / "first.yaml",
        """
id: p001
name: one
family: style_brief
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
  id: plain_text_v2
  canonicalizer: plain_text_v2
extractors:
  answer: style_brief_v1
required_capabilities: [chat_completions]
weight_hint: 0.5
tags: []
risk_level: low
""".strip(),
    )
    write_yaml(
        candidates_dir / "second.yaml",
        """
id: p001
name: two
family: style_brief
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
  id: plain_text_v2
  canonicalizer: plain_text_v2
extractors:
  answer: style_brief_v1
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
id: p002
name: two
family: style_brief
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
  id: plain_text_v2
  canonicalizer: plain_text_v2
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
        candidates_dir / "p001.yaml",
        """
id: p001
name: broken
family: style_brief
intent: missing generation and capabilities
messages:
  - role: user
    content: hello
output_contract:
  id: plain_text_v2
  canonicalizer: plain_text_v2
extractors:
  answer: style_brief_v1
weight_hint: 0.5
tags: []
risk_level: low
""".strip(),
    )

    with pytest.raises(Exception):
        load_candidate_prompts(candidates_dir)
