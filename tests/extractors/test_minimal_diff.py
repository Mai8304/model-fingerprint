from __future__ import annotations

from pathlib import Path

from modelfingerprint.extractors.minimal_diff import extract_minimal_diff

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractors" / "minimal_diff"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_minimal_diff_scores_small_change_spans() -> None:
    features = extract_minimal_diff(read_fixture("simple.patch"))

    assert features["changed_lines"] == 2
    assert features["touched_hunks"] == 1
    assert features["reorder_tendency"] is False
    assert features["minimality_score"] == 1.0


def test_minimal_diff_detects_reorders() -> None:
    features = extract_minimal_diff(read_fixture("reorder.patch"))

    assert features["changed_lines"] == 4
    assert features["reorder_tendency"] is True
    assert features["minimality_score"] < 1.0
