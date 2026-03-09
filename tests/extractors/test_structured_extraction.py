from __future__ import annotations

from pathlib import Path

from modelfingerprint.extractors.structured_extraction import extract_structured_extraction

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractors" / "structured_extraction"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_structured_extraction_scores_grounded_payloads() -> None:
    features = extract_structured_extraction(read_fixture("grounded.json"))

    assert features["field_accuracy"] == 1.0
    assert features["evidence_alignment"] == 1.0
    assert features["hallucinated_fields"] == 0
    assert features["missing_field_pattern"] == ""


def test_structured_extraction_surfaces_hallucinations_and_missing_fields() -> None:
    features = extract_structured_extraction(read_fixture("hallucinated.json"))

    assert features["field_accuracy"] == 0.5
    assert features["evidence_alignment"] == 0.5
    assert features["hallucinated_fields"] == 1
    assert features["missing_field_pattern"] == "role"
