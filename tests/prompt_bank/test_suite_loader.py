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
template: explain why event sourcing is not always the default
variables: []
output_contract:
  type: plain_text
extractor: style_brief_v1
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
template: produce a fixed JSON object
variables: []
output_contract:
  type: json
extractor: strict_format_v1
weight_hint: 0.6
tags: [format]
risk_level: low
""".strip(),
    )

    prompts = load_candidate_prompts(candidates_dir)

    assert list(prompts) == ["p001", "p002"]
    assert prompts["p001"].extractor == "style_brief_v1"


def test_screening_suite_must_be_strict_subset_of_default(tmp_path: Path) -> None:
    suites_dir = tmp_path / "prompt-bank" / "suites"
    write_yaml(
        suites_dir / "default-v1.yaml",
        """
id: default-v1
name: default v1
prompt_ids: [p001, p002, p003]
""".strip(),
    )
    write_yaml(
        suites_dir / "screening-v1.yaml",
        """
id: screening-v1
name: screening v1
prompt_ids: [p001, p002]
""".strip(),
    )

    suites = load_suites(suites_dir)

    validate_suite_subset(suites["default-v1"], suites["screening-v1"])


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
template: first
variables: []
output_contract:
  type: plain_text
extractor: style_brief_v1
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
template: second
variables: []
output_contract:
  type: plain_text
extractor: style_brief_v1
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
template: second
variables: []
output_contract:
  type: plain_text
extractor: made_up_v9
weight_hint: 0.5
tags: []
risk_level: low
""".strip(),
    )

    with pytest.raises(PromptBankValidationError):
        load_candidate_prompts(candidates_dir)
