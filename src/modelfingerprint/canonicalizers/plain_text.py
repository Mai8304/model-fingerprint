from __future__ import annotations

from modelfingerprint.canonicalizers.base import CanonicalizerResult
from modelfingerprint.contracts.run import CanonicalizedOutput


def canonicalize_plain_text(raw_output: str) -> CanonicalizerResult:
    return CanonicalizedOutput(format_id="plain_text_v2", payload={"text": raw_output.strip()}), []
