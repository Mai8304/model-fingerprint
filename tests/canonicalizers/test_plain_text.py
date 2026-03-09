from __future__ import annotations

from modelfingerprint.canonicalizers.plain_text import canonicalize_plain_text


def test_plain_text_canonicalizer_trims_outer_whitespace() -> None:
    canonical_output, events = canonicalize_plain_text("\n  Hello world.  \n")

    assert canonical_output.format_id == "plain_text_v2"
    assert canonical_output.payload == {"text": "Hello world."}
    assert events == []
