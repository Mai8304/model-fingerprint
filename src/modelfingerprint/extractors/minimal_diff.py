from __future__ import annotations

from collections import Counter

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.base import FeatureMap


def extract_minimal_diff(canonical_output: object) -> FeatureMap:
    text = _extract_text(canonical_output)
    lines = text.splitlines()
    changed_lines = [
        line
        for line in lines
        if (line.startswith("+") or line.startswith("-"))
        and not line.startswith(("+++", "---"))
    ]
    added = [line[1:] for line in changed_lines if line.startswith("+")]
    removed = [line[1:] for line in changed_lines if line.startswith("-")]
    touched_hunks = sum(line.startswith("@@") for line in lines)
    reorder_tendency = Counter(added) == Counter(removed) and added != removed and bool(added)

    return {
        "changed_lines": len(changed_lines),
        "touched_hunks": touched_hunks,
        "reorder_tendency": reorder_tendency,
        "minimality_score": max(0.0, 1.0 - max(0, len(changed_lines) - 2) / 4),
    }


def _extract_text(canonical_output: object) -> str:
    if not isinstance(canonical_output, CanonicalizedOutput):
        raise TypeError("minimal_diff_v1 expects CanonicalizedOutput input")
    text = canonical_output.payload.get("text")
    if not isinstance(text, str):
        raise TypeError("plain_text canonical payload must include a text string")
    return text
