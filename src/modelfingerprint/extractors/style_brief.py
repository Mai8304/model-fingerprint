from __future__ import annotations

import re

from modelfingerprint.extractors.base import FeatureMap

HEDGE_WORDS = ("probably", "maybe", "might", "possibly", "perhaps")


def extract_style_brief(raw_output: str) -> FeatureMap:
    normalized = " ".join(raw_output.split())
    lowered = normalized.lower()
    tokens = re.findall(r"[a-zA-Z']+", lowered)
    hedge_hits = sum(token in HEDGE_WORDS for token in tokens)

    return {
        "char_len": len(normalized),
        "sentence_count": _count_sentences(normalized),
        "opens_with_conclusion": lowered.startswith(("use ", "choose ", "conclusion")),
        "uses_numbered_list": bool(re.search(r"(?m)^\s*\d+\.", raw_output)),
        "hedge_density": hedge_hits / max(len(tokens), 1),
        "directness_score": 1.0 if hedge_hits == 0 else round(max(0.0, 1.0 - hedge_hits / 4), 3),
    }


def _count_sentences(text: str) -> int:
    return len([part for part in re.split(r"(?<!\d)[.!?]+", text) if part.strip()])
