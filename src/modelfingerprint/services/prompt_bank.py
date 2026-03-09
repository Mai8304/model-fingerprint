from __future__ import annotations

from pathlib import Path

import yaml

from modelfingerprint.contracts.prompt import PromptDefinition, SuiteDefinition

RESEARCH_SET_SUITE_ID = "research-set-v1"
FINGERPRINT_SUITE_ID = "fingerprint-suite-v1"
QUICK_CHECK_SUITE_ID = "quick-check-v1"

KNOWN_EXTRACTOR_IDS = frozenset(
    {
        "style_brief_v1",
        "strict_format_v1",
        "minimal_diff_v1",
        "structured_extraction_v1",
        "retrieval_v1",
    }
)


class PromptBankValidationError(ValueError):
    """Raised when prompt-bank files violate repository invariants."""


def load_candidate_prompts(directory: Path) -> dict[str, PromptDefinition]:
    prompts: dict[str, PromptDefinition] = {}

    for path in sorted(directory.glob("*.yaml")):
        prompt = PromptDefinition.model_validate(_read_yaml(path))

        if prompt.id in prompts:
            raise PromptBankValidationError(f"duplicate prompt id: {prompt.id}")
        if prompt.extractor not in KNOWN_EXTRACTOR_IDS:
            raise PromptBankValidationError(f"unknown extractor: {prompt.extractor}")

        prompts[prompt.id] = prompt

    return prompts


def load_suites(directory: Path) -> dict[str, SuiteDefinition]:
    suites: dict[str, SuiteDefinition] = {}

    for path in sorted(directory.glob("*.yaml")):
        suite = SuiteDefinition.model_validate(_read_yaml(path))
        suites[suite.id] = suite

    return suites


def validate_suite_subset(
    fingerprint_suite: SuiteDefinition,
    quick_check_suite: SuiteDefinition,
) -> None:
    fingerprint_ids = set(fingerprint_suite.prompt_ids)
    quick_check_ids = set(quick_check_suite.prompt_ids)

    if not quick_check_ids < fingerprint_ids:
        raise PromptBankValidationError(
            "quick-check suite must be a strict subset of fingerprint suite"
        )


def validate_suite_references(
    prompts: dict[str, PromptDefinition],
    suites: dict[str, SuiteDefinition],
) -> None:
    known_prompt_ids = set(prompts)

    for suite in suites.values():
        missing = [prompt_id for prompt_id in suite.prompt_ids if prompt_id not in known_prompt_ids]
        if missing:
            joined = ", ".join(missing)
            raise PromptBankValidationError(
                f"suite {suite.id} references unknown prompt ids: {joined}"
            )


def _read_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PromptBankValidationError(f"expected mapping payload in {path}")
    return data
