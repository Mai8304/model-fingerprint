from __future__ import annotations

from modelfingerprint.contracts.run import NormalizedCompletion
from modelfingerprint.extractors.base import FeatureMap


def extract_completion_metadata(completion: object) -> FeatureMap:
    if not isinstance(completion, NormalizedCompletion):
        raise TypeError("completion_metadata_v1 expects NormalizedCompletion input")

    latency_bucket_ms = None
    if completion.latency_ms is not None:
        latency_bucket_ms = (completion.latency_ms // 1000) * 1000

    return {
        "reasoning_visible": completion.reasoning_visible,
        "reasoning_tokens": completion.usage.reasoning_tokens,
        "finish_reason": completion.finish_reason or "",
        "latency_bucket_ms": 0 if latency_bucket_ms is None else latency_bucket_ms,
    }
