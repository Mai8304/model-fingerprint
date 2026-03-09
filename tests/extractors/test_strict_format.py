from __future__ import annotations

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.strict_format import extract_strict_format


def test_strict_format_extracts_semantic_values_from_strict_json_payload() -> None:
    features = extract_strict_format(
        CanonicalizedOutput(
            format_id="strict_json_v2",
            payload={"answer": "yes", "confidence": "high"},
        )
    )

    assert features["field_count"] == 2
    assert features["answer_value"] == "yes"
    assert features["confidence_value"] == "high"


def test_strict_format_extracts_semantic_values_from_tagged_text_payload() -> None:
    features = extract_strict_format(
        CanonicalizedOutput(
            format_id="tagged_text_v2",
            payload={"status": "blocked", "reason": "tests are failing"},
        )
    )

    assert features["field_count"] == 2
    assert features["status_value"] == "blocked"
    assert features["reason_value"] == "tests are failing"
