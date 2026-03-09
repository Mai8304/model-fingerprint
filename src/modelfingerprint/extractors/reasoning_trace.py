from __future__ import annotations

import re

from modelfingerprint.extractors.base import FeatureMap

HEDGE_WORDS = ("probably", "maybe", "might", "possibly", "perhaps")
BACKTRACK_MARKERS = ("however", "but", "instead", "wait", "reconsider", "revise")


def extract_reasoning_trace(reasoning_text: object) -> FeatureMap:
    if not isinstance(reasoning_text, str):
        raise TypeError("reasoning_trace_v1 expects reasoning text input")

    normalized = reasoning_text.strip()
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    lowered = normalized.lower()
    tokens = re.findall(r"[a-zA-Z']+", lowered)
    hedge_hits = sum(token in HEDGE_WORDS for token in tokens)
    backtrack_hits = sum(marker in lowered for marker in BACKTRACK_MARKERS)

    return {
        "step_count": len(lines),
        "uses_numbered_outline": any(re.match(r"^\d+\.", line) for line in lines),
        "hedge_density": hedge_hits / max(len(tokens), 1),
        "backtrack_markers": backtrack_hits,
    }
