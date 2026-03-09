# Dual-Dimension Fingerprint Design

**Problem**

The current pipeline primarily answers one question: does a run's prompt output look like an existing profile. That is useful, but it underweights a separate class of identity signals that users care about in practice: whether the endpoint supports core behaviors such as tools, visible thinking, streaming, and image generation. Recent black-box runs also showed a second issue: capability failures, provider rate limits, and "thinking without final answer" can distort the content score in ways that are hard to explain.

**Goal**

Add a first-class capability dimension, measured with minimal probes, and combine it with the existing prompt-content fingerprint so the system can say both:

- does this endpoint behave like the reference model at the capability layer
- do the actual prompt responses look like the reference model's content fingerprint

**Hard Constraints**

- Capability probes must be minimal.
- Capability probes must not rely on prompt-body features from the 10-question suite.
- `insufficient_evidence` must never be treated as `unsupported`.
- Provider and packaging variance must not dominate identity judgments when the actual response content is close.

**Approaches Considered**

1. Keep a single content-only similarity score.
   This remains simple, but it cannot explain capability mismatches and it overreacts to partial-answer thinking runs.
2. Merge capability outcomes into the existing feature vector without a separate dimension.
   This is workable internally, but it produces opaque scores and makes it difficult to distinguish "different model" from "same model through a different provider wrapper."
3. Add a separate capability dimension and combine it with content similarity at verdict time.
   This preserves the current content fingerprinting pipeline, makes capability mismatches explicit, and supports better user-facing explanations.

**Recommendation**

Use option 3.

## Design

### 1. External Model

The system should expose four top-level outputs for a comparison:

- `capability_similarity`
- `content_similarity`
- `overall_similarity`
- `verdict`

The verdict should no longer depend on content similarity alone.

### 2. Internal Split

Implementation should keep three internal objects:

- `capability_probe`
- `content_fingerprint`
- `final_verdict`

This allows the code to preserve the existing prompt-feature pipeline while making probe evidence auditable.

### 3. Minimal Capability Probes

Each capability probe must use the baseline request body plus the smallest possible delta needed to trigger that capability.

**Baseline chat body**

```json
{
  "model": "...",
  "messages": [{"role": "user", "content": "只返回 ok"}],
  "max_tokens": 32
}
```

**Probe definitions**

- `thinking`
  - Request: baseline only
  - Success evidence: visible reasoning field, or reasoning-token evidence if the provider exposes it
- `tools`
  - Request: baseline plus `tools` and forced `tool_choice`
  - Success evidence: `tool_calls` or `finish_reason=tool_calls`
- `streaming`
  - Request: baseline plus `stream: true`
  - Success evidence: SSE response with at least one delta chunk
- `image`
  - Request: image-generation route with the minimum required body for that route
  - Success evidence: image asset field such as `url` or `b64_json`

**Forbidden default fields for probes**

- `temperature`
- `top_p`
- `response_format`
- `reasoning`
- `stream` except for the streaming probe
- `tools` except for the tools probe
- provider-private tuning flags

### 4. Probe Outcome States

Each capability probe may emit exactly one of:

- `supported`
- `accepted_but_ignored`
- `unsupported`
- `insufficient_evidence`

Interpretation:

- `supported`: the capability-specific evidence was returned
- `accepted_but_ignored`: request succeeded but the expected capability result did not appear
- `unsupported`: the server explicitly rejected the capability
- `insufficient_evidence`: timeout, network issue, rate limit, regional restriction, or similar inconclusive failure

### 5. Capability Artifact Shape

Run artifacts should store the raw probe summary separately from prompt results.

```json
{
  "capability_probe": {
    "probe_mode": "minimal",
    "probe_version": "v1",
    "coverage_ratio": 0.75,
    "capabilities": {
      "thinking": {
        "status": "supported",
        "http_status": 200,
        "latency_ms": 1500,
        "detail": "reasoning field is populated",
        "evidence": {"field": "reasoning"}
      }
    }
  }
}
```

Profile artifacts should store aggregated capability distributions instead of a single frozen value.

```json
{
  "capability_profile": {
    "thinking": {
      "supported": 0.8,
      "accepted_but_ignored": 0.2
    }
  }
}
```

### 6. Capability Similarity

Capability similarity should be computed separately from prompt-content similarity.

Recommended per-capability weights:

- `thinking`: `0.35`
- `tools`: `0.30`
- `streaming`: `0.20`
- `image`: `0.15`

Rationale:

- `thinking` and `tools` are higher-signal identity markers in current black-box usage.
- `image` is more likely to reflect endpoint packaging and product routing, so it should carry the lowest weight.

Recommended state-match matrix:

| Reference | Target | Score |
|---|---|---:|
| `supported` | `supported` | `1.00` |
| `supported` | `accepted_but_ignored` | `0.55` |
| `supported` | `unsupported` | `0.00` |
| `accepted_but_ignored` | `supported` | `0.75` |
| `accepted_but_ignored` | `accepted_but_ignored` | `1.00` |
| `unsupported` | `unsupported` | `1.00` |
| `unsupported` | `supported` | `0.35` |

If either side is `insufficient_evidence`, do not score that capability. Instead, reduce `capability_coverage_ratio`.

### 7. Content Similarity

Content similarity should continue to use the current v2 prompt pipeline:

- `score.*`
- `answer.*`
- `reasoning.*`
- `transport.*`
- `surface.*`

The key change is that content similarity is no longer overloaded to represent capability identity.

### 8. Overall Similarity

Recommended default:

`overall_similarity = 0.7 * content_similarity + 0.3 * capability_similarity`

This keeps prompt behavior primary while still letting capability mismatches matter.

### 9. Coverage and Verdict Rules

Two coverage numbers now matter:

- `content_coverage_ratio`
- `capability_coverage_ratio`

Verdict rules:

- `match`
  - content is high
  - capability is high
  - no hard mismatch
- `suspicious`
  - content is high
  - but capability has a meaningful conflict
- `mismatch`
  - content is not close, or core capability evidence clearly disagrees
- `insufficient_evidence`
  - content coverage is too low, or capability coverage is too low
- `unknown`
  - enough evidence exists, but similarity is below the known-model threshold

### 10. Hard Mismatches

Only two capability gaps should trigger a hard mismatch by default:

- reference profile is stably `thinking=supported`, target is clearly `thinking=unsupported`
- reference profile is stably `tools=supported`, target is clearly `tools=unsupported`

`streaming` and `image` should influence score and explanation, but should not by themselves force a hard mismatch.

### 11. Why This Fixes the Recent Failure Modes

- A model that emits long visible thinking but no final answer will score poorly on content coverage, but it can still look capability-similar.
- A provider-side `429` will no longer be translated into a false capability mismatch.
- A model can match the content fingerprint of GLM-5 while still being flagged as suspicious if its core capability shape is clearly different.

## Testing

- Contract tests for new run/profile/comparison fields
- Capability-probe tests for minimal request bodies and outcome classification
- Profile-builder tests for capability distribution aggregation
- Comparator tests for:
  - content-only match with weak capability evidence
  - strong capability mismatch with strong content similarity
  - `insufficient_evidence` behavior when probe coverage is too low
- CLI/e2e tests showing the new dual-dimension output

## Non-Goals

- Do not infer tool, image, or streaming support from the 10 prompt responses.
- Do not add video probing in this iteration.
- Do not replace the current prompt-content fingerprint with embeddings or opaque vector search.
