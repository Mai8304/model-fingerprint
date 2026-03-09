from __future__ import annotations

from pathlib import Path

from modelfingerprint.extractors.retrieval import extract_retrieval

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractors" / "retrieval"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_retrieval_extracts_hits_and_confusion_patterns() -> None:
    features = extract_retrieval(read_fixture("mixed_hits.json"))

    assert features["needle_hit_count"] == 2
    assert features["wrong_needle_type"] == 1
    assert features["order_preservation"] is False
    assert features["confusion_pattern"] == "delta"
