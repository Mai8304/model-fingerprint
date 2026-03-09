# Thinking Model Fallback Design

**Problem**

Some reasoning-capable models on OpenRouter can consume the entire output-token budget on reasoning tokens before emitting a final answer. For fingerprint prompts that require strict, scoreable JSON, this produces `finish_reason=length` with `message.content=null`, which is not a stable baseline.

**Goal**

Add a configurable endpoint-level fallback policy so thinking models can still be fingerprinted reproducibly without relying on one-off scripts.

**Approaches Considered**

1. Raise the output budget globally.
   This reduces truncation but materially changes cost and latency, and it does not guarantee better final answers.
2. Force `reasoning.effort=none` for all runs.
   This is stable for scoreable prompts but discards a useful capability signal.
3. Use a retry ladder.
   Start with a configurable reasoning mode, retry with a larger token budget when the model truncates before answering, then fall back to an answer-first mode when needed.

**Recommendation**

Use option 3.

**Design**

- Add optional endpoint-level request overrides for OpenAI-compatible transports.
- Add an optional `thinking_policy` block to endpoint profiles.
- `thinking_policy` defines:
  - whether the endpoint should use thinking fallbacks
  - a sequence of retry attempts, each with output-token multiplier/cap and optional reasoning override
- `LiveRunner` keeps the existing HTTP retry loop for transport failures.
- On successful HTTP responses, `LiveRunner` additionally evaluates completion quality:
  - if the model truncated before producing an answer, or returned no answer text, and a thinking policy exists, it retries with the next configured attempt
  - otherwise it returns the completion immediately
- Each retry attempt is written to the trace request payload so the run is auditable.
- The final run artifact keeps existing prompt output features. Thinking fallback usage is observable from traces and endpoint policy, but the first implementation does not add a new feature channel.

**GLM-5 Policy**

- Initial attempt: preserve current behavior and allow visible reasoning when available.
- Retry 1: raise output budget to a bounded larger token cap.
- Retry 2: disable visible reasoning via request override so the model emits a scoreable answer.

**Why Not Characters**

OpenRouter budgets are token-based. Character counts are not the right control surface and are not portable across models/providers.

**Testing**

- Contract tests for new endpoint fields.
- Live runner tests for retry ladder behavior:
  - no retry when first attempt succeeds
  - retry on truncated/no-answer completion
  - stop once a later attempt yields answer text
  - preserve existing transport retry semantics
