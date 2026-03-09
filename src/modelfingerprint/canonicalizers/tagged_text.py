from __future__ import annotations

import re

from modelfingerprint.canonicalizers.base import CanonicalizationError, CanonicalizerResult
from modelfingerprint.contracts.run import CanonicalizedOutput

TAG_PATTERN = re.compile(r"<(?P<tag>status|reason)>(?P<value>.*?)</(?P=tag)>", re.DOTALL)


def canonicalize_tagged_text(raw_output: str) -> CanonicalizerResult:
    stripped = raw_output.strip()
    payload: dict[str, object] = {}
    consumed: list[str] = []
    for match in TAG_PATTERN.finditer(stripped):
        tag = match.group("tag")
        payload[tag] = match.group("value").strip()
        consumed.append(match.group(0))

    if set(payload) != {"status", "reason"}:
        raise CanonicalizationError(
            code="invalid_tagged_text",
            message="response must contain exactly <status> and <reason> tags",
        )

    remainder = stripped
    for token in consumed:
        remainder = remainder.replace(token, "", 1)
    if remainder.strip():
        raise CanonicalizationError(
            code="unexpected_text",
            message="response contains text outside the required tags",
        )

    return CanonicalizedOutput(format_id="tagged_text_v2", payload=payload), []
