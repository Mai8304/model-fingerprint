from __future__ import annotations

from modelfingerprint.contracts.run import CanonicalizationEvent, CanonicalizedOutput
from modelfingerprint.extractors.base import SurfaceExtractorInput
from modelfingerprint.extractors.surface_contract import extract_surface_contract


def test_surface_contract_detects_clean_tolerant_json_contract_retention() -> None:
    features = extract_surface_contract(
        SurfaceExtractorInput(
            raw_output='{"task_result":{},"evidence":{},"unknowns":{},"violations":[]}',
            canonical_output=CanonicalizedOutput(
                format_id="tolerant_json_v3",
                payload={"task_result": {}, "evidence": {}, "unknowns": {}, "violations": []},
            ),
        )
    )

    assert features["had_markdown_fence"] is False
    assert features["has_extra_text"] is False
    assert features["parse_repaired"] is False
    assert features["repair_event_count"] == 0
    assert features["has_extra_prefix_text"] is False
    assert features["has_extra_suffix_text"] is False
    assert features["key_alias_normalized"] is False
    assert features["field_order_match"] is True
    assert features["constraint_retention"] is True


def test_surface_contract_detects_fences_extra_text_and_order_drift() -> None:
    features = extract_surface_contract(
        SurfaceExtractorInput(
            raw_output=(
                'Here is the result:\n```json\n'
                '{"evidence":{},"task_result":{},"unknowns":{},"violations":[]}\n```'
            ),
            canonical_output=CanonicalizedOutput(
                format_id="tolerant_json_v3",
                payload={"task_result": {}, "evidence": {}, "unknowns": {}, "violations": []},
            ),
        )
    )

    assert features["had_markdown_fence"] is True
    assert features["has_extra_text"] is True
    assert features["parse_repaired"] is False
    assert features["field_order_match"] is False
    assert features["constraint_retention"] is False


def test_surface_contract_records_parse_repairs_for_tolerant_json() -> None:
    features = extract_surface_contract(
        SurfaceExtractorInput(
            raw_output='结果如下：{"result":{},"evidence_map":{},"unknown_fields":{},"violations":[]}',
            canonical_output=CanonicalizedOutput(
                format_id="tolerant_json_v3",
                payload={"task_result": {}, "evidence": {}, "unknowns": {}, "violations": []},
            ),
            canonicalization_events=[
                CanonicalizationEvent(
                    code="stripped_prefix_text",
                    message="removed explanatory text before JSON object",
                ),
                CanonicalizationEvent(
                    code="normalized_key_alias",
                    message="normalized top-level key aliases to canonical names",
                ),
            ],
        )
    )

    assert features["has_extra_text"] is True
    assert features["parse_repaired"] is True
    assert features["repair_event_count"] == 2
    assert features["has_extra_prefix_text"] is True
    assert features["has_extra_suffix_text"] is False
    assert features["key_alias_normalized"] is True
