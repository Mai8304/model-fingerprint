from __future__ import annotations

from modelfingerprint.canonicalizers._common import parse_json_object
from modelfingerprint.canonicalizers.base import CanonicalizerResult
from modelfingerprint.contracts.run import CanonicalizedOutput


def canonicalize_strict_json(raw_output: str) -> CanonicalizerResult:
    payload, events = parse_json_object(raw_output)
    return CanonicalizedOutput(format_id="strict_json_v2", payload=payload), events
