# A0 Thinking-Aware Fingerprint Architecture and Interface Plan

**Goal:** Replace the bootstrap v1 protocol with a production-oriented v2 architecture that can fingerprint both non-thinking and thinking-capable models without treating transport quirks, provider wrappers, or semantically equivalent output shapes as model-identity evidence.

**Status:** Planned on 2026-03-09

**Decision:** Backward compatibility with the current bootstrap contracts is not required. v2 may replace the current prompt schema, live transport layer, artifact contracts, and comparison flow if the result is cleaner and more durable.

---

## 1. Why v2 is required

The current repository proved the basic offline flow, but it still has five architecture gaps:

1. Live runs only preserve final `content`; they do not preserve exposed reasoning text, reasoning-token usage, or dialect-specific metadata.
2. The transport boundary assumes a single generic OpenAI-compatible response shape, which is too weak for reasoning fields, usage-field variants, and JSON-mode differences.
3. Released prompts are not yet fully self-contained protocol objects. Some live runs required ad hoc supplemental context outside the prompt-bank definition.
4. Extractors currently conflate surface formatting with semantic content and are too brittle against equivalent JSON shapes.
5. Run artifacts only model successful prompt outputs. They do not preserve prompt-level failure status, capability mismatch, truncation, or timeout evidence as first-class data.

v2 fixes those gaps directly instead of layering incremental compatibility shims on top of the bootstrap path.

---

## 2. Product goals and non-goals

### 2.1 Goals

1. Support thinking-aware fingerprinting:
   - capture `final answer`
   - capture `exposed reasoning text` when available
   - capture `reasoning token` usage when available
   - keep reasoning separate from answer-channel scoring
2. Design the live stack by `protocol dialect + capability profile`, not by provider brand.
3. Freeze released fingerprint protocols:
   - fixed prompt messages
   - fixed embedded context
   - fixed generation parameters
   - fixed canonicalization rules
4. Separate `protocol execution compatibility` from `model fingerprint similarity`.
5. Accept semantically equivalent output shapes through canonicalization so format variance is not misread as identity evidence.
6. Preserve prompt-level operational evidence:
   - timeout
   - truncation
   - unsupported capability
   - invalid response
   - canonicalization warnings
7. Produce reproducible file artifacts suitable for offline review, calibration, and audit.

### 2.2 Non-goals for this v2 cycle

1. Tool-calling or multi-turn agent benchmarking.
2. Streaming-by-default operator UX. Streaming support may exist in the transport, but the core protocol remains request/response per prompt.
3. Cross-provider secret management beyond environment-variable based runtime injection.

---

## 3. Architecture decisions

### 3.1 Separate answer, reasoning, and transport channels

v2 treats one prompt execution as three distinct evidence channels:

1. `answer channel`
   - the final answer text returned by the model
2. `reasoning channel`
   - the exposed thinking / reasoning text if the endpoint reveals it
3. `transport channel`
   - finish reason
   - latency
   - usage
   - truncation
   - visible capability behavior

Only the answer channel is universal. Reasoning and transport channels are optional but first-class. They must never be concatenated into the answer text.

### 3.2 Design by dialect, configure by endpoint profile

v2 must not create one code adapter per provider brand. It must instead split the live layer into:

1. `dialect adapters`
   - small number of code paths
   - each handles one request/response wire protocol family
2. `endpoint profiles`
   - declarative YAML files
   - describe capability flags and field paths for a specific endpoint

Examples of likely v2 dialects:

1. `openai_chat_v1`
2. `anthropic_messages_v1`
3. `gemini_generate_content_v1`

Examples of endpoint-profile concerns:

1. answer text path
2. reasoning text path
3. usage field names
4. supported JSON response mode
5. output-token parameter alias
6. retry / timeout defaults
7. whether reasoning exposure is expected

### 3.3 Released suites are immutable protocol contracts

For released suites such as `fingerprint-suite-v1` and `quick-check-v1`, each prompt definition must include:

1. full message list
2. fixed embedded context
3. fixed generation parameters
4. declared output contract
5. declared canonicalizer
6. declared answer/reasoning/transport extractor ids
7. required capability flags

Runtime code may translate field names for a dialect, but it may not:

1. lower `max_output_tokens`
2. inject extra context
3. rewrite the prompt
4. switch JSON mode on or off
5. change timeout or retry policy in a way that changes the semantic protocol

If an endpoint cannot satisfy the released protocol, the result is `incompatible` or `insufficient evidence`, not “adaptive success”.

### 3.4 Canonicalization precedes feature extraction

Each prompt execution must pass through:

1. raw completion capture
2. output-contract canonicalization
3. feature extraction

Canonicalization must be tolerant where semantics are equivalent. Examples:

1. `hallucinated: false` and `hallucinated: []`
2. JSON wrapped in markdown fences
3. key aliases such as `due date` vs `due_date`
4. `evidence` represented as a list of field names vs field-to-evidence mapping, when the target semantic contract allows both

Canonicalization events must be recorded so we preserve auditability without conflating those events with identity evidence.

### 3.5 Incomplete runs are first-class artifacts

Every prompt in a run must be preserved even when it fails. v2 must record prompt-level status such as:

1. `completed`
2. `timeout`
3. `transport_error`
4. `unsupported_capability`
5. `truncated`
6. `invalid_response`
7. `canonicalization_error`

Comparison must use scoreable prompts only, while separately reporting:

1. answer coverage
2. reasoning coverage
3. missing / failed prompt ids
4. protocol compatibility findings

---

## 4. End-to-end v2 flow

1. Validate prompt-bank definitions and endpoint-profile definitions.
2. Materialize one immutable request per prompt from the released suite definition.
3. Pass the request through the selected dialect adapter using the selected endpoint profile.
4. Parse the raw wire response into a `NormalizedCompletion`.
5. Canonicalize the answer channel according to the prompt’s output contract.
6. Extract answer, reasoning, and transport features into a prompt-level feature map.
7. Persist a `RunArtifact` that includes every prompt, including failures.
8. Build `ProfileArtifact` objects from repeated baseline runs.
9. Calibrate suite thresholds with coverage-aware statistics.
10. Compare a suspect run against stored profiles and report:
    - similarity breakdown
    - coverage breakdown
    - protocol compatibility findings
    - final verdict

---

## 5. Contract model

### 5.1 Prompt definition

Each released prompt definition becomes a complete protocol object:

```yaml
id: p007
name: evidence_grounded_extraction
family: structured_extraction
intent: measure grounded extraction under fixed evidence references
messages:
  - role: system
    content: You are a precise extraction engine. Return only the requested structure.
  - role: user
    content: |
      Extract name and role from the supplied text only, and attach evidence ids for every field.

      Supplied text:
      [e1] Alice is the primary database administrator for the payments team.
      [e2] She rotated on-call last week.
      [e3] The team is migrating reporting jobs next quarter.
generation:
  temperature: 0.0
  top_p: 1.0
  max_output_tokens: 256
  response_format: json_object
  reasoning_mode: capture_if_available
output_contract:
  id: structured_extraction_v2
  canonicalizer: structured_extraction_v2
extractors:
  answer: structured_extraction_v2
  reasoning: reasoning_trace_v1
  transport: completion_metadata_v1
required_capabilities:
  - chat_completions
  - json_object_response
weight_hint: 0.9
tags: [extraction, evidence]
risk_level: low
```

Required schema changes:

1. replace `template` with `messages`
2. move fixed generation parameters into the prompt definition
3. add `output_contract`
4. add `extractors.answer`
5. add optional `extractors.reasoning`
6. add optional `extractors.transport`
7. add `required_capabilities`

### 5.2 Endpoint profile

Endpoint profiles are configuration, not secret stores:

```yaml
id: siliconflow-openai-chat
dialect: openai_chat_v1
base_url: https://api.siliconflow.cn/v1
auth:
  kind: bearer_env
  env_var: MODEL_FINGERPRINT_API_KEY
capabilities:
  exposes_reasoning_text: true
  supports_json_object_response: true
  supports_temperature: true
  supports_top_p: true
  supports_output_token_cap: true
request_mapping:
  output_token_cap_field: max_tokens
  json_response_shape:
    type: json_object
response_mapping:
  answer_text_path: choices.0.message.content
  reasoning_text_path: choices.0.message.reasoning_content
  finish_reason_path: choices.0.finish_reason
  usage_paths:
    prompt_tokens: usage.prompt_tokens
    output_tokens: usage.completion_tokens
    total_tokens: usage.total_tokens
    reasoning_tokens: usage.completion_tokens_details.reasoning_tokens
timeout_policy:
  connect_seconds: 10
  read_seconds: 120
retry_policy:
  max_attempts: 3
  retryable_statuses: [408, 429, 500, 502, 503, 504]
```

Important rule:

- endpoint profiles may map the semantic output-token cap to another request field name
- they may not silently change the value

### 5.3 Normalized completion

Each dialect adapter must return a single normalized envelope:

```json
{
  "answer_text": "...",
  "reasoning_text": "...",
  "reasoning_visible": true,
  "finish_reason": "stop",
  "latency_ms": 18342,
  "usage": {
    "prompt_tokens": 112,
    "output_tokens": 87,
    "reasoning_tokens": 612,
    "total_tokens": 811
  },
  "raw_response_path": "traces/2026-03-09/run-123/p007.response.json"
}
```

### 5.4 Prompt execution record

Each prompt execution in a run must include:

1. prompt id
2. execution status
3. normalized request snapshot
4. normalized completion if present
5. canonical output if produced
6. canonicalization events
7. extracted features
8. error object if not completed

### 5.5 Run artifact

Run artifacts must include all prompts, not only successes.

Required run-level summary fields:

1. `prompt_count_total`
2. `prompt_count_completed`
3. `prompt_count_scoreable`
4. `answer_coverage_ratio`
5. `reasoning_coverage_ratio`
6. `protocol_compatibility`
7. `trace_dir`

### 5.6 Profile artifact

Profiles remain statistical summaries over repeated runs, but v2 adds:

1. weighted prompt summaries
2. answer / reasoning / transport feature namespaces
3. expected reasoning visibility summary
4. coverage statistics

### 5.7 Comparison report

Comparison output must distinguish protocol execution quality from fingerprint similarity:

1. `overall_similarity`
2. `answer_similarity`
3. `reasoning_similarity`
4. `transport_similarity`
5. `answer_coverage_ratio`
6. `reasoning_coverage_ratio`
7. `protocol_compatibility`
8. `missing_prompt_ids`
9. `failed_prompt_ids`
10. `verdict`

Recommended verdict set:

1. `match`
2. `suspicious`
3. `unknown`
4. `insufficient_evidence`
5. `incompatible_protocol`

---

## 6. Canonicalization model

Canonicalization must be explicit, typed, and testable.

### 6.1 Required properties

1. deterministic
2. lossless where possible
3. records every normalization event
4. rejects only true semantic ambiguity, not harmless shape variance

### 6.2 v2 canonicalizers to implement

1. `plain_text_v2`
2. `strict_json_v2`
3. `tagged_text_v2`
4. `structured_extraction_v2`
5. `retrieval_v2`

### 6.3 Canonicalization examples

Equivalent and accepted:

1. fenced JSON vs raw JSON
2. `hallucinated: false` vs `hallucinated: []`
3. `"due date"` vs `"due_date"` as canonical field key
4. evidence values as strings or one-element arrays

Not equivalent and must remain visible as behavior:

1. extra hallucinated field names
2. missing requested fields
3. reordered retrieval result when order is part of the contract
4. extra prose outside a contract that explicitly forbids extra text

The second group may still canonicalize for semantic extraction, but must emit surface-behavior features so we do not lose operator insight.

---

## 7. Thinking-aware feature model

### 7.1 Feature namespaces

To avoid mixing channels, v2 uses namespaced features:

1. `answer.*`
2. `reasoning.*`
3. `transport.*`
3. `surface.*`

Example:

1. `answer.field_accuracy`
2. `reasoning.char_len`
3. `reasoning.self_correction_markers`
4. `transport.reasoning_visible`
5. `surface.has_markdown_fence`

### 7.2 Required generic reasoning features

The first v2 release should include generic reasoning features that do not depend on private chain-of-thought semantics:

1. `reasoning.char_len`
2. `reasoning.step_count`
3. `reasoning.has_numbered_outline`
4. `reasoning.backtrack_marker_count`
5. `reasoning.hedge_density`
6. `transport.reasoning_visible`
7. `transport.reasoning_token_ratio`

Reasoning text is optional evidence, not required on every prompt.

### 7.3 Surface vs semantic behavior

For JSON-like prompts, v2 must keep both:

1. semantic features from canonicalized payload
2. surface features from the original answer text

This is the mechanism that solves:

- “格式不一致完全可能仍然是同一个模型”

Semantically equivalent shapes should remain close on semantic features, while surface habits remain available as lower-weight auxiliary evidence.

---

## 8. Scoring, coverage, and calibration

### 8.1 Weighted prompt scoring

Unlike the bootstrap implementation, v2 scoring must use prompt weights from the released suite.

For each prompt:

1. compute feature-level scores
2. compute channel-level scores
3. combine channels by configured prompt/channel weights

For the run:

1. compute weighted answer similarity
2. compute weighted reasoning similarity where available
3. compute weighted transport similarity
4. compute weighted overall similarity

### 8.2 Coverage gates

Comparison must never hide low coverage behind one number.

At minimum, report:

1. `answer_coverage_ratio`
2. `reasoning_coverage_ratio`
3. whether required prompt families were covered
4. whether the endpoint satisfied the released protocol capabilities

Recommended gating behavior:

1. below minimum answer coverage -> `insufficient_evidence`
2. reasoning required but hidden -> `incompatible_protocol` or `insufficient_evidence`
3. endpoint cannot honor mandatory protocol feature -> `incompatible_protocol`

### 8.3 Calibration changes

Calibration must be updated to record:

1. same-model and cross-model similarity stats
2. answer coverage stats
3. reasoning coverage stats
4. minimum acceptable coverage thresholds
5. protocol compatibility expectations for the suite

---

## 9. Required directory layout changes

v2 introduces or formalizes:

```text
endpoint-profiles/
  openai-chat/
    deepseek-chat.yaml
    siliconflow-openai-chat.yaml
prompt-bank/
  candidates/
  suites/
traces/
  2026-03-09/
    run-id/
      p001.request.json
      p001.response.json
schemas/
src/modelfingerprint/
  canonicalizers/
  dialects/
  transports/
  services/
```

`traces/` are runtime artifacts and should remain untracked by git.

---

## 10. CLI surface required by v2

The final operator surface should include at least:

1. `validate-prompts`
2. `validate-endpoints`
3. `show-suite`
4. `show-endpoint`
5. `run-suite`
6. `build-profile`
7. `calibrate`
8. `compare`

`run-suite` must support:

1. fixture mode
2. live mode with endpoint profile
3. explicit API key env var or direct secret input
4. no adaptive prompt rewriting
5. no adaptive token-cap lowering

---

## 11. Acceptance criteria for the full v2 program

The v2 program is complete only when all of the following are true:

1. released prompt definitions are fully self-contained protocol objects
2. live runs preserve answer text, reasoning text, usage, finish reason, latency, and raw trace references
3. endpoint profiles are validated as structured config
4. at least one real dialect adapter is implemented and fully tested
5. canonicalization handles semantically equivalent JSON shapes without extractor crashes
6. failed prompts are preserved in run artifacts as typed statuses
7. profiles and comparisons are coverage-aware and weight-aware
8. CLI can run the complete suite in fixture mode end-to-end
9. CLI can run at least one live dialect path behind a non-default test marker or manual smoke path
10. docs explain the difference between:
    - protocol compatibility
    - exposed reasoning availability
    - fingerprint similarity

---

## 12. Execution order

Implement v2 in the following order:

1. `2026-03-09-mf-v2-p0-contracts-and-fixed-protocol.md`
2. `2026-03-09-mf-v2-p1-dialect-normalization-and-endpoint-profiles.md`
3. `2026-03-09-mf-v2-p2-canonicalization-and-thinking-feature-pipeline.md`
4. `2026-03-09-mf-v2-p3-profile-calibration-and-comparison-v2.md`
5. `2026-03-09-mf-v2-p4-cli-live-e2e-and-operator-guides.md`

This order is mandatory because each later phase depends on the contracts and invariants introduced by the earlier phase.
