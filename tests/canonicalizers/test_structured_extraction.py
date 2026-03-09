from __future__ import annotations

import pytest

from modelfingerprint.canonicalizers.base import CanonicalizationError
from modelfingerprint.canonicalizers.structured_extraction import (
    canonicalize_structured_extraction,
)


def test_structured_extraction_canonicalizer_normalizes_equivalent_shapes() -> None:
    canonical_output, events = canonicalize_structured_extraction(
        """
        ```json
        {
          "requested_fields": ["owner", "due date"],
          "extracted": {"owner": "alice", "due date": "2026-03-09"},
          "evidence": {"owner": ["e1"], "due date": ["e2"]},
          "hallucinated": false
        }
        ```
        """
    )

    assert canonical_output.format_id == "structured_extraction_v2"
    assert canonical_output.payload == {
        "requested_fields": ["owner", "due_date"],
        "extracted": {"owner": "alice", "due_date": "2026-03-09"},
        "evidence_fields": ["due_date", "owner"],
        "hallucinated": [],
    }
    assert {event.code for event in events} == {
        "removed_fence",
        "normalized_key_alias",
        "normalized_evidence_shape",
        "coerced_false_to_empty_list",
    }


def test_structured_extraction_canonicalizer_rejects_non_mapping_extracted_payload() -> None:
    with pytest.raises(CanonicalizationError, match="extracted"):
        canonicalize_structured_extraction(
            '{"requested_fields":["name"],"extracted":["alice"],"evidence":["name"],"hallucinated":[]}'
        )
