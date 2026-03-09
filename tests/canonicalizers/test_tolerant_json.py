from __future__ import annotations

import pytest

from modelfingerprint.canonicalizers.base import CanonicalizationError
from modelfingerprint.canonicalizers.tolerant_json import canonicalize_tolerant_json


def test_tolerant_json_canonicalizer_accepts_prefix_suffix_and_fence() -> None:
    canonical_output, events = canonicalize_tolerant_json(
        '这里是结果：\n```json\n{"task_result":{},"evidence":{},"unknowns":{},"violations":[]}\n```\n谢谢'
    )

    assert canonical_output.format_id == "tolerant_json_v3"
    assert canonical_output.payload == {
        "task_result": {},
        "evidence": {},
        "unknowns": {},
        "violations": [],
    }
    assert [event.code for event in events] == [
        "removed_fence",
        "stripped_prefix_text",
        "stripped_suffix_text",
    ]


def test_tolerant_json_canonicalizer_normalizes_top_level_aliases() -> None:
    canonical_output, events = canonicalize_tolerant_json(
        '{"result":{},"evidence_map":{},"unknown_fields":{},"violations":[]}'
    )

    assert canonical_output.payload == {
        "task_result": {},
        "evidence": {},
        "unknowns": {},
        "violations": [],
    }
    assert [event.code for event in events] == ["normalized_key_alias"]


def test_tolerant_json_canonicalizer_rejects_outputs_that_need_semantic_guessing() -> None:
    with pytest.raises(CanonicalizationError, match="JSON object"):
        canonicalize_tolerant_json("owner is Alice Wong")


def test_tolerant_json_canonicalizer_rejects_non_object_payloads() -> None:
    with pytest.raises(CanonicalizationError, match="JSON object"):
        canonicalize_tolerant_json('["not","an","object"]')
