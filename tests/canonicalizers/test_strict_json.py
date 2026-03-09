from __future__ import annotations

import pytest

from modelfingerprint.canonicalizers.base import CanonicalizationError
from modelfingerprint.canonicalizers.strict_json import canonicalize_strict_json


def test_strict_json_canonicalizer_accepts_markdown_fences() -> None:
    canonical_output, events = canonicalize_strict_json(
        '```json\n{"answer":"yes","confidence":"high"}\n```'
    )

    assert canonical_output.format_id == "strict_json_v2"
    assert canonical_output.payload == {"answer": "yes", "confidence": "high"}
    assert [event.code for event in events] == ["removed_fence"]


def test_strict_json_canonicalizer_rejects_non_object_payloads() -> None:
    with pytest.raises(CanonicalizationError, match="JSON object"):
        canonicalize_strict_json('["yes","high"]')
