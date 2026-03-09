from __future__ import annotations

from collections.abc import Mapping, Sequence

from modelfingerprint.canonicalizers._common import normalize_key, parse_json_object
from modelfingerprint.canonicalizers.base import CanonicalizationError, CanonicalizerResult
from modelfingerprint.contracts.run import CanonicalizationEvent, CanonicalizedOutput


def canonicalize_structured_extraction(raw_output: str) -> CanonicalizerResult:
    payload, events = parse_json_object(raw_output)
    normalized_key_used = False

    requested_fields = payload.get("requested_fields", [])
    if not isinstance(requested_fields, Sequence) or isinstance(requested_fields, (str, bytes)):
        raise CanonicalizationError(
            code="invalid_requested_fields",
            message="requested_fields must be a list of strings",
        )
    normalized_requested: list[str] = []
    for item in requested_fields:
        if not isinstance(item, str):
            raise CanonicalizationError(
                code="invalid_requested_fields",
                message="requested_fields must be a list of strings",
            )
        normalized, changed = normalize_key(item)
        normalized_key_used = normalized_key_used or changed
        normalized_requested.append(normalized)

    extracted = payload.get("extracted", {})
    if not isinstance(extracted, Mapping):
        raise CanonicalizationError(
            code="invalid_extracted",
            message="extracted must be a JSON object",
        )
    normalized_extracted: dict[str, str] = {}
    for key, value in extracted.items():
        if not isinstance(key, str):
            raise CanonicalizationError(
                code="invalid_extracted",
                message="extracted must use string keys",
            )
        normalized_key_value, changed = normalize_key(key)
        normalized_key_used = normalized_key_used or changed
        normalized_extracted[normalized_key_value] = str(value)

    evidence = payload.get("evidence", [])
    normalized_evidence_fields: list[str]
    evidence_shape_changed = False
    if isinstance(evidence, Mapping):
        normalized_evidence_fields = []
        evidence_shape_changed = True
        for key, value in evidence.items():
            if not isinstance(key, str):
                raise CanonicalizationError(
                    code="invalid_evidence",
                    message="evidence mapping must use string keys",
                )
            if not _has_evidence(value):
                continue
            normalized_key_value, changed = normalize_key(key)
            normalized_key_used = normalized_key_used or changed
            normalized_evidence_fields.append(normalized_key_value)
        normalized_evidence_fields = sorted(set(normalized_evidence_fields))
    elif isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
        normalized_evidence_fields = []
        for item in evidence:
            if not isinstance(item, str):
                raise CanonicalizationError(
                    code="invalid_evidence",
                    message="evidence list must contain only strings",
                )
            normalized_key_value, changed = normalize_key(item)
            normalized_key_used = normalized_key_used or changed
            normalized_evidence_fields.append(normalized_key_value)
        normalized_evidence_fields = sorted(set(normalized_evidence_fields))
    else:
        raise CanonicalizationError(
            code="invalid_evidence",
            message="evidence must be a list or object",
        )

    hallucinated = payload.get("hallucinated", [])
    normalized_hallucinated: list[str]
    if hallucinated is False:
        normalized_hallucinated = []
        events.append(
            CanonicalizationEvent(
                code="coerced_false_to_empty_list",
                message="coerced hallucinated false to an empty list",
            )
        )
    elif isinstance(hallucinated, Sequence) and not isinstance(hallucinated, (str, bytes)):
        normalized_hallucinated = []
        for item in hallucinated:
            if not isinstance(item, str):
                raise CanonicalizationError(
                    code="invalid_hallucinated",
                    message="hallucinated must be false or a list of strings",
                )
            normalized_key_value, changed = normalize_key(item)
            normalized_key_used = normalized_key_used or changed
            normalized_hallucinated.append(normalized_key_value)
    else:
        raise CanonicalizationError(
            code="invalid_hallucinated",
            message="hallucinated must be false or a list of strings",
        )

    if normalized_key_used:
        events.append(
            CanonicalizationEvent(
                code="normalized_key_alias",
                message="normalized key aliases to canonical snake_case form",
            )
        )
    if evidence_shape_changed:
        events.append(
            CanonicalizationEvent(
                code="normalized_evidence_shape",
                message="normalized evidence mapping to evidence_fields list",
            )
        )

    canonical_payload: dict[str, object] = {
        "requested_fields": normalized_requested,
        "extracted": normalized_extracted,
        "evidence_fields": normalized_evidence_fields,
        "hallucinated": normalized_hallucinated,
    }
    return (
        CanonicalizedOutput(format_id="structured_extraction_v2", payload=canonical_payload),
        events,
    )


def _has_evidence(value: object) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return len(value) > 0
    return True
