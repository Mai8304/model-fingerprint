from __future__ import annotations

from modelfingerprint.canonicalizers.retrieval import canonicalize_retrieval


def test_retrieval_canonicalizer_accepts_fenced_json_without_fixing_wrong_needles() -> None:
    canonical_output, events = canonicalize_retrieval(
        """
        ```json
        {
          "expected_needles": ["alpha", "beta", "gamma"],
          "found_needles": ["alpha", "delta", "gamma"]
        }
        ```
        """
    )

    assert canonical_output.format_id == "retrieval_v2"
    assert canonical_output.payload == {
        "expected_needles": ["alpha", "beta", "gamma"],
        "found_needles": ["alpha", "delta", "gamma"],
    }
    assert [event.code for event in events] == ["removed_fence"]
