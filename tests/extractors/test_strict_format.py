from __future__ import annotations

from pathlib import Path

from modelfingerprint.extractors.strict_format import extract_strict_format

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "extractors" / "strict_format"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_strict_format_accepts_clean_json_object() -> None:
    features = extract_strict_format(read_fixture("clean_object.json"))

    assert features["valid_format"] is True
    assert features["has_extra_text"] is False
    assert features["field_order_match"] is True


def test_strict_format_detects_extra_text_and_order_drift() -> None:
    features = extract_strict_format(read_fixture("extra_text.txt"))

    assert features["valid_format"] is False
    assert features["has_extra_text"] is True
    assert features["field_order_match"] is False
