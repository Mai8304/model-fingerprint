from __future__ import annotations

from pathlib import Path

from modelfingerprint.contracts.run import CanonicalizedOutput
from modelfingerprint.extractors.style_brief import extract_style_brief

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractors" / "style_brief"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_style_brief_extracts_stable_short_response_features() -> None:
    features = extract_style_brief(
        CanonicalizedOutput(
            format_id="plain_text_v2",
            payload={"text": read_fixture("direct_response.txt")},
        )
    )

    assert features["char_len"] == 45
    assert features["sentence_count"] == 2
    assert features["uses_numbered_list"] is False
    assert features["directness_score"] == 1.0


def test_style_brief_detects_lists_and_hedging() -> None:
    features = extract_style_brief(
        CanonicalizedOutput(
            format_id="plain_text_v2",
            payload={"text": read_fixture("numbered_hedged.txt")},
        )
    )

    assert features["uses_numbered_list"] is True
    assert features["sentence_count"] == 3
    assert features["hedge_density"] > 0.0
