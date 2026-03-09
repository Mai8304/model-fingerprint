from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.structured_extraction import extract_structured_extraction

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractors" / "structured_extraction"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_structured_extraction_scores_grounded_payloads() -> None:
    payload = json.loads(read_fixture("grounded.json"))
    features = extract_structured_extraction(
        CanonicalizedOutput(
            format_id="structured_extraction_v2",
            payload={
                "requested_fields": payload["requested_fields"],
                "extracted": payload["extracted"],
                "evidence_fields": payload["evidence"],
                "hallucinated": payload["hallucinated"],
            },
        )
    )

    assert features["field_accuracy"] == 1.0
    assert features["evidence_alignment"] == 1.0
    assert features["hallucinated_fields"] == 0
    assert features["missing_field_pattern"] == ""


def test_structured_extraction_surfaces_hallucinations_and_missing_fields() -> None:
    payload = json.loads(read_fixture("hallucinated.json"))
    features = extract_structured_extraction(
        CanonicalizedOutput(
            format_id="structured_extraction_v2",
            payload={
                "requested_fields": payload["requested_fields"],
                "extracted": payload["extracted"],
                "evidence_fields": payload["evidence"],
                "hallucinated": payload["hallucinated"],
            },
        )
    )

    assert features["field_accuracy"] == 0.5
    assert features["evidence_alignment"] == 0.5
    assert features["hallucinated_fields"] == 1
    assert features["missing_field_pattern"] == "role"
