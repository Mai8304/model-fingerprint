from __future__ import annotations

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import SurfaceExtractorInput
from modelfingerprint.extractors.surface_contract import extract_surface_contract


def test_surface_contract_detects_clean_strict_json_contract_retention() -> None:
    features = extract_surface_contract(
        SurfaceExtractorInput(
            raw_output='{"answer":"yes","confidence":"high"}',
            canonical_output=CanonicalizedOutput(
                format_id="strict_json_v2",
                payload={"answer": "yes", "confidence": "high"},
            ),
        )
    )

    assert features["had_markdown_fence"] is False
    assert features["has_extra_text"] is False
    assert features["field_order_match"] is True
    assert features["constraint_retention"] is True


def test_surface_contract_detects_fences_extra_text_and_order_drift() -> None:
    features = extract_surface_contract(
        SurfaceExtractorInput(
            raw_output='Here is the result:\n```json\n{"confidence":"high","answer":"yes"}\n```',
            canonical_output=CanonicalizedOutput(
                format_id="strict_json_v2",
                payload={"answer": "yes", "confidence": "high"},
            ),
        )
    )

    assert features["had_markdown_fence"] is True
    assert features["has_extra_text"] is True
    assert features["field_order_match"] is False
    assert features["constraint_retention"] is False
