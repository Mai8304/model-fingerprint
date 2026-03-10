# Thinking-Aware Runtime Execution Design

**Problem**

The repository now has three strong pieces in place:

1. minimal capability probes for `thinking`, `tools`, `streaming`, and `image`
2. content fingerprint suites (`fingerprint-suite-v2` and `fingerprint-suite-v3`)
3. deterministic comparison and verdict code in Python

The missing layer is the live runtime policy that connects those pieces.

Today, `run-suite` probes capabilities first, but the probe result does not drive transport behavior. The actual runtime still depends on endpoint-level static timeout fields and optional endpoint-specific `thinking_policy` ladders. This causes three operational problems:

1. the code does not consistently wait longer for endpoints that expose visible thinking
2. one prompt can still stall or abort the suite if the transport path raises the wrong kind of exception
3. the output budget used for live content prompts is still prompt-local or endpoint-local, not a fixed runtime policy

Recent black-box runs exposed the result: some thinking endpoints return long reasoning traces, empty final answers, or read-time hangs; operators then need ad hoc manual reruns and interpretation. That is not acceptable for a product path that must run entirely under Python control.

**Goal**

Add a first-class, code-only runtime execution policy that:

- keeps capability probes minimal and unchanged
- classifies endpoints as `thinking` or `non-thinking` from probe output
- applies deterministic timeout windows and retry rounds per prompt
- solidifies a `3000` token live content output budget in code
- never lets one prompt block the entire suite
- persists enough attempt metadata for audit, debugging, and product output

**Status**

Planned on 2026-03-10.

---

## 1. Current State

### 1.1 What the code already does

The current main branch already supports:

- minimal capability probing in `src/modelfingerprint/services/capability_probe.py`
- capability-aware run/profile/comparison artifacts
- comparison artifacts and JSON schema export
- endpoint-level OpenAI-compatible thinking fallback via `EndpointProfile.thinking_policy`

Relevant files:

- `src/modelfingerprint/cli.py`
- `src/modelfingerprint/services/capability_probe.py`
- `src/modelfingerprint/transports/live_runner.py`
- `src/modelfingerprint/transports/http_client.py`
- `src/modelfingerprint/services/suite_runner.py`
- `src/modelfingerprint/dialects/openai_chat.py`
- `src/modelfingerprint/contracts/run.py`

### 1.2 What the code does not yet do

The current code does **not** yet implement the runtime flow agreed in discussion:

1. capability-probe `thinking` results do not drive timeout or retry behavior
2. there is no code-level distinction between:
   - `thinking => 30s + 30s window`
   - `non-thinking => 30s window`
3. there is no fixed global live content output-token budget of `3000`
4. there is no prompt-attempt model that records per-window behavior
5. suite execution still relies on a narrow transport error boundary; some unexpected exceptions can abort the whole run

### 1.3 Why this matters

Without a runtime policy layer, the product still depends on:

- endpoint-specific heuristics
- manual reruns
- manual trace inspection

That is the opposite of the intended deployment model. The product should behave deterministically from Python code alone.

---

## 2. Hard Requirements

### 2.1 Functional requirements

1. Capability probes remain minimal and unchanged in shape.
2. Live content prompt execution must classify the endpoint as `thinking` or `non-thinking`.
3. `thinking` endpoints must use a `30s + 30s` execution window per round.
4. `non-thinking` endpoints must use a single `30s` execution window per round.
5. If a round finishes without a usable answer, the runtime must perform one more round.
6. If the second round still fails, the runtime must skip the prompt and continue to the next prompt.
7. Live content requests must use a code-level output token cap of `3000` when the endpoint supports output caps.
8. All orchestration decisions must live in Python code, not in LLM judgment or manual operator logic.

### 2.2 Operational requirements

1. A failed prompt must not block the suite.
2. The runtime must persist enough structured attempt metadata to explain:
   - how many windows were used
   - which round succeeded or failed
   - why the prompt stopped retrying
3. Probe outcomes such as `insufficient_evidence` must not be misclassified as unsupported capability.
4. Capability probes must keep their current minimal request bodies and small token budgets.

### 2.3 Non-goals

1. Do not redesign the minimal capability probes themselves.
2. Do not add video probing in this cycle.
3. Do not replace deterministic similarity logic with LLM-as-judge.
4. Do not require streaming transport for the new runtime.

---

## 3. Approaches Considered

### Option 1: Keep endpoint-level `thinking_policy` as the primary runtime control

This would preserve the existing `EndpointProfile` pattern and let each endpoint keep custom retry ladders.

Pros:

- smallest immediate code change
- preserves current OpenRouter GLM-5 behavior

Cons:

- does not satisfy the requirement that runtime logic be productized and code-driven from capability probe results
- keeps operator behavior endpoint-specific
- does not address the fixed `3000` token budget requirement cleanly

### Option 2: Put runtime behavior entirely in CLI glue code

The CLI could probe capabilities, then run custom loops around `LiveRunner`.

Pros:

- simple initial implementation
- leaves `LiveRunner` mostly unchanged

Cons:

- duplicates runtime logic outside the transport boundary
- makes non-CLI reuse harder
- pushes too much orchestration into top-level command code

### Option 3: Add a dedicated runtime-policy layer and make `LiveRunner` policy-driven

Capability probes stay minimal. CLI resolves a runtime policy from probe output. `LiveRunner` executes prompts against that policy. `SuiteRunner` guarantees per-prompt isolation. Run artifacts record the policy and per-attempt outcomes.

Pros:

- satisfies the product requirement
- keeps capability probe, transport execution, and artifact reporting aligned
- makes the runtime deterministic and testable

Cons:

- requires contract, transport, and schema work

**Recommendation:** Use option 3.

---

## 4. Proposed Architecture

### 4.1 Overview

The new runtime layer has five parts:

1. `Capability Probe`  
   Existing minimal probes remain unchanged.

2. `Runtime Policy Resolver`  
   New Python code maps probe output to a concrete execution policy.

3. `LiveRunner Policy Executor`  
   `LiveRunner` executes prompt rounds and attempt windows according to the resolved policy.

4. `Prompt Attempt Recording`  
   Each prompt stores structured attempt metadata in the run artifact.

5. `Suite-Level Isolation`  
   `SuiteRunner` guarantees that one prompt failure does not terminate the suite.

### 4.2 Control flow

1. CLI loads endpoint profile and API key.
2. CLI runs `probe_capabilities(...)`.
3. CLI resolves `RuntimeExecutionPolicy` from the probe payload.
4. CLI constructs `LiveRunner(endpoint, api_key, dialect, runtime_policy, ...)`.
5. `SuiteRunner` iterates prompts.
6. `LiveRunner` executes each prompt with:
   - prompt request body
   - runtime output token cap
   - prompt-round attempt schedule
7. `FeaturePipeline` scores any completed prompt normally.
8. `RunArtifact` stores:
   - content features
   - capability probe
   - runtime policy snapshot
   - per-prompt attempt summaries

### 4.3 Why the resolver lives between probe and transport

The capability probe should remain a pure observation tool.

The transport should remain a pure execution tool.

The policy resolver is the clean place to encode product rules such as:

- what counts as a `thinking` endpoint
- how many windows belong to a round
- how many rounds are allowed
- what output token cap applies to live content prompts

This split keeps the code easy to test and easy to evolve.

---

## 5. Runtime Policy

### 5.1 Thinking classification

The runtime must classify endpoints conservatively:

- `thinking` if and only if `capability_probe.results.thinking.status == "supported"`
- otherwise `non-thinking`

Reasoning:

- `supported` is the only state that positively proves visible thinking
- `accepted_but_ignored`, `unsupported`, and `insufficient_evidence` must not silently opt the runtime into longer waits

The policy snapshot should record both:

- the observed probe status
- the resolved execution class

### 5.2 Content output token budget

For live suite execution only:

- if the endpoint supports output token caps, set the live content output token cap to `3000`
- capability probes keep their current minimal token budgets
- fixture mode remains unchanged

Rationale:

- this fixes the current operator need to manually rerun models with larger budgets
- it applies only to content prompt execution, not minimal capability detection

### 5.3 Round and window model

The runtime must use two nested levels:

1. `round`
   - a complete opportunity to produce a usable answer for one prompt

2. `window`
   - one concrete HTTP execution attempt inside a round

Resolved schedules:

- `thinking`
  - `round_windows_seconds = [30, 30]`
  - `max_rounds = 2`
- `non-thinking`
  - `round_windows_seconds = [30]`
  - `max_rounds = 2`

This means:

- `thinking` prompts may consume up to 4 HTTP attempts
- `non-thinking` prompts may consume up to 2 HTTP attempts

This is intentional. The implementation must model the "30s check" as a discrete attempt window, not as an LLM-supervised pause.

### 5.4 What counts as a usable result

A prompt attempt succeeds and stops execution only when the result is scoreable as a real answer-bearing completion.

At minimum, these statuses should stop the prompt as successful or final:

- `completed`
- `unsupported_capability`
- `canonicalization_error`
- `invalid_response` with answer text present but malformed contract output

These should remain retryable within the runtime schedule:

- transport timeout
- retryable transport error
- empty answer text
- truncated output

### 5.5 Prompt stop conditions

A prompt stops when one of the following occurs:

1. a usable completed answer is produced
2. a non-retryable terminal result is produced
3. all windows in the current round are exhausted and the retry round is also exhausted

If stop condition 3 is reached, the prompt result is persisted and the suite continues to the next prompt.

---

## 6. Data Model Changes

### 6.1 New runtime policy snapshot

Add a run-level snapshot to `RunArtifact`.

Suggested shape:

```json
{
  "runtime_policy": {
    "policy_id": "thinking-aware-runtime-v1",
    "thinking_probe_status": "supported",
    "execution_class": "thinking",
    "round_windows_seconds": [30, 30],
    "max_rounds": 2,
    "output_token_cap": 3000
  }
}
```

### 6.2 New prompt-attempt summary

Add attempt-level metadata to `PromptRunResult`.

Suggested shape:

```json
{
  "attempts": [
    {
      "round_index": 1,
      "window_index": 1,
      "read_timeout_seconds": 30,
      "http_attempt_index": 1,
      "output_token_cap": 3000,
      "status": "timeout",
      "error_kind": "timeout",
      "http_status": null,
      "latency_ms": 30019,
      "finish_reason": null,
      "answer_text_present": false,
      "reasoning_visible": null
    }
  ]
}
```

These summaries must be written by Python runtime code, not reconstructed later by LLM analysis.

### 6.3 Backward compatibility

The contracts should be extended, not replaced:

- older runs without `runtime_policy` remain valid
- older prompt results without `attempts` remain valid

This allows existing v2/v3 artifacts to remain readable.

---

## 7. Component-Level Design

### 7.1 `services/runtime_policy.py` (new)

Add a new module responsible for:

- defining runtime constants
- resolving probe payload into a runtime policy object
- exposing a small number of deterministic helper functions

Recommended constants:

- `LIVE_CONTENT_OUTPUT_TOKEN_CAP = 3000`
- `THINKING_ROUND_WINDOWS_SECONDS = [30, 30]`
- `NON_THINKING_ROUND_WINDOWS_SECONDS = [30]`
- `MAX_PROMPT_ROUNDS = 2`

### 7.2 `cli.py`

`run-suite` should:

1. probe capabilities
2. resolve runtime policy from the probe payload
3. pass the resolved runtime policy into `LiveRunner`

This keeps the current operator flow unchanged while moving the logic into code.

### 7.3 `live_runner.py`

`LiveRunner` must become policy-driven:

- ignore capability-driven runtime behavior no longer being derived from endpoint `thinking_policy`
- execute rounds and windows from the resolved runtime policy
- always apply the runtime output token cap for live content prompts
- return a prompt result instead of raising when transport or parse errors occur
- capture per-window attempt summaries

Existing endpoint `thinking_policy` should be treated as legacy behavior and should not be the primary runtime decision path for suite execution.

### 7.4 `http_client.py`

The HTTP client can remain request/response based, but it must support:

- caller-provided read timeout per window
- stable translation of timeout, network, HTTP, and invalid JSON errors

No LLM-dependent interpretation is allowed at this layer.

### 7.5 `suite_runner.py`

`SuiteRunner` must be hardened so that:

- transport exceptions do not abort the suite
- one prompt always yields one `PromptExecutionResult`
- the suite always reaches the final prompt unless the whole process is terminated externally

---

## 8. Interaction with Existing Endpoint Profiles

### 8.1 Endpoint timeout fields

Retain `EndpointProfile.timeout_policy.connect_seconds` as the connect timeout source.

Read timeout for live content prompts must be derived from runtime policy windows, not from the endpoint profile's static read timeout.

### 8.2 Endpoint retry policy

Retain `EndpointProfile.retry_policy` for transport-level retryability classification and retryable status codes.

The new runtime policy sits above that layer:

- HTTP retryability still matters within a single window attempt
- prompt rounds and windows are the new product-level retry model

### 8.3 Endpoint `thinking_policy`

For this delivery:

- keep the contract field for backward compatibility
- stop relying on it as the main execution strategy for live suite prompts

Later cleanup may remove or shrink it, but that is out of scope for this cycle.

---

## 9. Failure Model

### 9.1 Retryable prompt outcomes

These should consume the next window or next round:

- timeout
- retryable transport error
- empty final answer
- truncated output

### 9.2 Non-retryable prompt outcomes

These should terminate the prompt immediately:

- unsupported capability
- malformed but non-empty answer that can be scored as invalid response
- canonicalization error after a non-empty answer
- prompt-level contract incompatibility

### 9.3 Suite-level guarantee

The suite must continue after any prompt-level final result, including:

- timeout after all rounds
- transport failure after all rounds
- truncated after all rounds
- invalid response after all rounds

The only acceptable reasons for a suite not to finish are:

- process termination
- explicit operator interruption
- catastrophic failure before the suite loop starts

---

## 10. Testing Strategy

### 10.1 Unit tests

Add or extend tests for:

- runtime policy resolution
- run contract validation with runtime policy and attempts
- live runner round/window behavior
- live runner fixed output token cap application
- suite runner continue-on-failure behavior

### 10.2 Integration tests

Cover:

- `run-suite` wiring from capability probe to runtime policy
- schema export for updated run contracts
- trace naming for multi-window attempts

### 10.3 End-to-end tests

Verify with fixtures that:

- `thinking` endpoints use two windows per round
- `non-thinking` endpoints use one window per round
- two rounds are attempted at most
- a failed prompt does not stop later prompts from running

### 10.4 Live smoke tests

After implementation, use at least:

- one visible-thinking endpoint
- one non-thinking endpoint

Validation goals:

- run completes end-to-end
- output budget is `3000`
- prompts are skipped instead of blocking indefinitely
- run artifact shows correct runtime policy and prompt-attempt summaries

---

## 11. Rollout and Execution Order

This work should ship in four stages.

### Stage P0: Runtime policy contracts and resolver

Introduce:

- runtime-policy module
- run contract extensions
- schema export updates
- focused unit tests

### Stage P1: Live runner and HTTP execution loop

Implement:

- round/window execution model
- fixed `3000` live output budget
- prompt attempt recording
- broad prompt-level failure capture

### Stage P2: Suite wiring and operator-facing reporting

Implement:

- CLI wiring from probe to runtime policy
- suite continue-on-failure hardening
- show-run/reporting updates if needed
- e2e coverage

### Stage P3: Live validation, artifact refresh, and docs closure

Run:

- one thinking endpoint
- one non-thinking endpoint

Then:

- inspect artifacts
- update docs with observed behavior
- commit and push final validated state

---

## 12. Acceptance Criteria

This feature is complete only when all of the following are true:

1. `run-suite` uses capability-probe thinking results to choose runtime execution class.
2. Live content prompts use:
   - `thinking => [30, 30] windows x 2 rounds`
   - `non-thinking => [30] window x 2 rounds`
3. Live content prompts use a fixed `3000` output token cap when supported.
4. One failed prompt never prevents later prompts from executing.
5. Run artifacts persist runtime policy and prompt-attempt summaries.
6. Updated schemas validate.
7. Focused tests, lint, and mypy pass.
8. At least one live thinking endpoint and one live non-thinking endpoint complete a smoke run under the new code path.

