from __future__ import annotations

from collections import Counter

from modelfingerprint.extractors.base import FeatureMap


def extract_minimal_diff(raw_output: str) -> FeatureMap:
    lines = raw_output.splitlines()
    changed_lines = [
        line for line in lines if (line.startswith("+") or line.startswith("-")) and not line.startswith(("+++", "---"))
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
