from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.retrieval import extract_retrieval

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractors" / "retrieval"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_retrieval_extracts_hits_and_confusion_patterns() -> None:
    payload = json.loads(read_fixture("mixed_hits.json"))
    features = extract_retrieval(
        CanonicalizedOutput(format_id="retrieval_v2", payload=payload)
    )

    assert features["needle_hit_count"] == 2
    assert features["wrong_needle_type"] == 1
    assert features["order_preservation"] is False
    assert features["confusion_pattern"] == "delta"
