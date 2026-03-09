from __future__ import annotations

from modelfingerprint.contracts.run import NormalizedCompletion, UsageMetadata
from modelfingerprint.extractors.completion_metadata import extract_completion_metadata


def test_completion_metadata_extracts_transport_features() -> None:
    features = extract_completion_metadata(
        NormalizedCompletion(
            answer_text='{"answer":"yes","confidence":"high"}',
            reasoning_text="1. inspect\n2. answer",
            reasoning_visible=True,
            finish_reason="stop",
            latency_ms=18342,
            usage=UsageMetadata(
                input_tokens=12,
                output_tokens=18,
                reasoning_tokens=24,
                total_tokens=54,
            ),
        )
    )

    assert features["reasoning_visible"] is True
    assert features["reasoning_tokens"] == 24
    assert features["finish_reason"] == "stop"
    assert features["latency_bucket_ms"] == 18000
