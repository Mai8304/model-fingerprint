from __future__ import annotations

from modelfingerprint.extractors.reasoning_trace import extract_reasoning_trace


def test_reasoning_trace_extracts_outline_hedges_and_backtracks() -> None:
    features = extract_reasoning_trace(
        "1. inspect the request\n"
        "2. maybe verify the required fields\n"
        "However, revise the output to remove commentary.\n"
        "3. return strict json"
    )

    assert features["step_count"] == 4
    assert features["uses_numbered_outline"] is True
    assert features["hedge_density"] > 0.0
    assert features["backtrack_markers"] >= 1
