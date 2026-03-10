# Single-Request Progress Runtime Design

**Problem**

The repository now has a capability-aware runtime layer, but its execution semantics do not match the agreed product behavior for thinking endpoints.

What is currently implemented:

1. `run-suite` probes minimal capabilities first.
2. A runtime policy is resolved from the capability probe.
3. `LiveRunner` executes prompts under that runtime policy.
4. A fixed live content output cap of `3000` tokens is available in code.

What is still wrong:

1. a `30s` runtime window currently maps to a new HTTP request, not to an in-flight progress check on the existing request
2. repeated prompt resubmission can amplify provider throttling and distort model behavior
3. the runtime cannot distinguish:
   - no response bytes yet
   - partial response body is arriving
   - full parseable response has completed
4. operators still need to reason manually about whether the endpoint was truly stalled or simply still streaming a long thinking-heavy response

That behavior is specifically wrong for thinking models. The user requirement is to inspect the state of the current response body, not to re-issue the prompt every `30s`.

**Goal**

Replace the current prompt-window retry semantics with a single-request, progress-aware runtime policy that:

- keeps capability probes minimal and unchanged
- classifies content execution as `thinking` or `non-thinking`
- never re-sends a prompt merely because a checkpoint elapsed
- checks in-flight response progress at deterministic checkpoints
- aborts only when the request shows no useful progress or exceeds a hard wall-clock deadline
- continues to the next prompt without blocking the suite
- records enough structured execution state for debugging, product output, and future comparison features

**Status**

Planned on 2026-03-10. This design supersedes the execution semantics from [2026-03-10-thinking-aware-runtime-execution-design.md](/Users/zhuangwei/Downloads/coding/modelfingerprint/docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md) while preserving the existing capability-probe, comparison, and artifact foundations.

---

## 1. Current State

### 1.1 What already exists in code

The repository already has the following production-relevant pieces:

- minimal capability probes in `src/modelfingerprint/services/capability_probe.py`
- deterministic runtime policy resolution in `src/modelfingerprint/services/runtime_policy.py`
- prompt-level execution in `src/modelfingerprint/transports/live_runner.py`
- a standard HTTP transport in `src/modelfingerprint/transports/http_client.py`
- run artifacts that persist:
  - `runtime_policy`
  - prompt-level `attempts`
- fixed `3000` live content output cap resolution

This means the problem is not "lack of runtime infrastructure". The problem is the semantics of how that runtime is executed.

### 1.2 What is wrong with the current runtime semantics

Today the policy-driven execution path in `LiveRunner` treats each runtime window as a full HTTP request attempt:

- `thinking` => `30s`, then a new request, then the next round, then another new request
- `non-thinking` => a single `30s` request per round, then a new request if the round fails

This conflicts with the agreed behavior:

- the runtime should inspect the state of the current response
- it should not re-send prompts simply because `30s` has elapsed
- frequent prompt resubmission can trigger rate limits and invalidate "same prompt, same request" assumptions

### 1.3 Why this matters operationally

Thinking endpoints commonly exhibit one of these patterns:

1. no bytes for a while, then a complete response
2. no bytes for a while, then a long partial response body, then a complete JSON object
3. partial bytes continue for a long time but no final parseable payload is ever completed

The runtime must distinguish those cases. Otherwise:

- a healthy but slow endpoint is misclassified as failed
- a stalled endpoint is retried too aggressively
- suite behavior becomes provider-dependent instead of code-deterministic

---

## 2. Requirements

### 2.1 Hard functional requirements

1. Capability probes remain minimal and unchanged.
2. Capability probes are still the only source of `thinking` classification.
3. A content prompt is issued once per prompt-level attempt.
4. Elapsed checkpoints inspect in-flight response state; they do not trigger a new prompt submission by themselves.
5. A prompt is successful only when the runtime has a full HTTP response and that response is parseable by the dialect.
6. Partial body arrival is treated as "progress", not as prompt completion.
7. The suite must continue after prompt failure or abort.
8. All orchestration logic lives in Python code.
9. The live content output cap remains fixed at `3000` when supported by the endpoint.

### 2.2 Thinking vs non-thinking execution requirements

The product requirement remains class-aware:

- `thinking`
  - first checkpoint at `30s`
  - second no-data checkpoint at `60s`
  - once data has begun arriving, poll progress every `10s`
  - total wall-clock deadline per prompt-level request: `120s`

- `non-thinking`
  - one no-data checkpoint at `30s`
  - if data has begun arriving by then, poll progress every `10s`
  - total wall-clock deadline per prompt-level request: `120s`

### 2.3 Progress definitions

The runtime must use explicit code-level definitions:

- `has_any_data`
  - at least one response body byte has been received
- `making_progress`
  - new bytes have been received within the last `10s`
- `completed_parseable_response`
  - the worker has a full HTTP response body and the dialect can parse it into a `NormalizedCompletion`

### 2.4 Abort conditions

The runtime must abort the current prompt-level request when either condition is met:

- no data has arrived by the last allowed no-data checkpoint
- total elapsed wall-clock time exceeds `120s` without a completed parseable response

### 2.5 Non-goals

1. Do not redesign capability probes.
2. Do not add video probing.
3. Do not convert similarity scoring into an LLM judge.
4. Do not require the provider to support SSE or explicit streaming APIs.
5. Do not add prompt-level repeated resubmission as the default success path.

---

## 3. Approaches Considered

### Option 1: Keep the current round/window semantics and merely lengthen timeouts

Pros:

- smallest code delta
- reuses current `LiveRunner` loops

Cons:

- still re-sends prompts
- still couples checkpoint expiration to new API calls
- does not satisfy the core product requirement

### Option 2: Add explicit API streaming mode and require SSE for progress checks

Pros:

- progress semantics are clearer if the provider supports SSE
- easy to detect chunk arrival

Cons:

- not all providers expose or reliably support SSE
- would overload the current capability dimension with a transport requirement
- violates the need to work from the existing non-streaming API surface

### Option 3: Use a single request attempt with an in-flight progress monitor

Pros:

- directly matches the agreed behavior
- avoids unnecessary prompt resubmission
- works for both thinking and non-thinking endpoints
- keeps orchestration fully in Python

Cons:

- requires new transport primitives
- requires thread-safe or non-blocking progress observation
- requires contract changes for richer progress metadata

**Recommendation:** Use option 3.

---

## 4. Proposed Architecture

### 4.1 High-level flow

1. `run-suite` probes capabilities.
2. `resolve_runtime_policy(...)` classifies the endpoint as `thinking` or `non-thinking` and returns checkpoint/deadline settings.
3. `LiveRunner` issues one prompt-level HTTP request attempt.
4. The HTTP transport exposes an in-flight progress handle.
5. `LiveRunner` polls that handle at deterministic checkpoints.
6. If the response completes and parses, the prompt succeeds.
7. If the response shows no allowed progress, the prompt attempt is aborted.
8. `SuiteRunner` records the prompt result and continues to the next prompt.

### 4.2 Separation of concerns

The design intentionally keeps roles separate:

- `Capability Probe`
  - observes provider behavior with minimal requests
- `Runtime Policy Resolver`
  - converts capability evidence into execution class and timing parameters
- `HTTP Client`
  - owns the in-flight request, byte counters, cancellation, and raw completion/error transport state
- `LiveRunner`
  - owns prompt-level checkpoint decisions and completion classification
- `SuiteRunner`
  - owns prompt isolation across the suite

### 4.3 Why the transport layer must change

The current `HttpClient.send(...)` API is blocking and only returns after the full response body has been read or the request has failed.

That is not enough for the new requirement. The runtime needs:

- byte-level progress visibility
- the ability to inspect a request while it is still in flight
- the ability to cancel a stalled request

Therefore the transport must expose a new in-flight request abstraction. This is a transport concern, not an LLM concern.

---

## 5. Runtime Policy Semantics

### 5.1 Execution class mapping

Execution class remains conservative:

- `thinking` only if `capability_probe.results.thinking.status == "supported"`
- otherwise `non-thinking`

This preserves the existing product assumption that only positive evidence should opt a model into the more permissive thinking schedule.

### 5.2 Proposed runtime policy fields

The current `RuntimePolicySnapshot` must evolve from "round windows" to "single-request monitoring semantics".

Recommended fields:

```json
{
  "policy_id": "single_request_progress_runtime_v1",
  "thinking_probe_status": "supported",
  "execution_class": "thinking",
  "no_data_checkpoints_seconds": [30, 60],
  "progress_poll_interval_seconds": 10,
  "total_deadline_seconds": 120,
  "output_token_cap": 3000
}
```

For `non-thinking`, `no_data_checkpoints_seconds` becomes `[30]`.

### 5.3 Why round-based fields should be retired

The existing fields:

- `round_windows_seconds`
- `max_rounds`

encode a mental model that each checkpoint is a separate HTTP attempt. That is no longer correct.

Best practice here is to:

- add the new policy fields
- keep old fields optional for backward compatibility if needed
- stop using old fields in new live execution code

That preserves old run artifacts while aligning new runs with the actual execution semantics.

---

## 6. In-Flight HTTP Monitoring Model

### 6.1 New transport abstraction

Introduce a progress-aware in-flight request abstraction. The exact class name may vary, but the capability must exist in code.

Recommended interface:

```python
class InFlightHttpRequest(Protocol):
    def snapshot(self) -> HttpProgressSnapshot: ...
    def wait_until_terminal(self, timeout_seconds: float) -> HttpTerminalResult | None: ...
    def cancel(self) -> None: ...
```

Recommended snapshot fields:

- `bytes_received`
- `has_any_data`
- `completed`
- `terminal_error_kind`
- `first_byte_latency_ms`
- `last_progress_latency_ms`
- `elapsed_ms`

### 6.2 Threaded implementation strategy

The most pragmatic implementation is:

1. keep the current blocking stdlib HTTP implementation in a worker thread
2. update shared progress state whenever body bytes are received
3. let the main thread poll that state at `30s`, `60s`, and `10s` intervals
4. on abort, signal cancellation and close the underlying connection

This is preferred over a full async rewrite because:

- it keeps the codebase small
- it minimizes dialect and CLI churn
- it allows incremental rollout on top of the existing HTTP client

### 6.3 Connection cancellation requirements

Cancellation must not rely on LLM behavior. The in-flight request must stop because Python closes the transport path or the worker honors a cancel signal.

Recommended behavior:

- body reads use short socket timeouts, such as `<= 1s`
- worker checks `cancel_event` between read calls
- if cancellation occurs, the connection is closed and the request settles into a deterministic terminal error

---

## 7. Prompt-Level State Machine

### 7.1 States

The runtime should explicitly model these states:

- `pending_no_data`
- `receiving_partial_response`
- `completed_parseable_response`
- `aborted_no_data_timeout`
- `aborted_total_timeout`
- `aborted_transport_error`
- `aborted_parse_error`

### 7.2 Thinking state machine

For `thinking` prompts:

1. start one HTTP request
2. at `30s`:
   - if completed and parseable, succeed
   - if data exists, move to progress polling
   - if no data, continue
3. at `60s`:
   - if completed and parseable, succeed
   - if data exists, move to progress polling
   - if still no data, abort request and fail the prompt
4. once in progress polling:
   - every `10s`, inspect the in-flight snapshot
   - if completed and parseable, succeed
   - if total elapsed > `120s`, abort and fail
   - otherwise continue polling the same request

### 7.3 Non-thinking state machine

For `non-thinking` prompts:

1. start one HTTP request
2. at `30s`:
   - if completed and parseable, succeed
   - if data exists, move to progress polling
   - if still no data, abort request and fail the prompt
3. once in progress polling:
   - every `10s`, inspect the same request
   - if completed and parseable, succeed
   - if total elapsed > `120s`, abort and fail
   - otherwise continue polling

### 7.4 Why partial data is not prompt completion

The product requirement is explicit: success means "full HTTP response and parseable".

Therefore:

- partial bytes
- partial JSON text
- a long reasoning prefix with no final answer object

must all remain in the "in progress" bucket until the body is complete and parseable.

---

## 8. Artifact and Schema Changes

### 8.1 Runtime policy snapshot

Add or replace runtime policy fields to represent the new semantics:

- `policy_id`
- `thinking_probe_status`
- `execution_class`
- `no_data_checkpoints_seconds`
- `progress_poll_interval_seconds`
- `total_deadline_seconds`
- `output_token_cap`

### 8.2 Prompt attempt summary

The current attempt summary must evolve to represent monitored request attempts rather than synthetic round/window retries.

Recommended fields:

- `request_attempt_index`
- `read_timeout_seconds`
- `output_token_cap`
- `status`
- `error_kind`
- `http_status`
- `latency_ms`
- `finish_reason`
- `answer_text_present`
- `reasoning_visible`
- `bytes_received`
- `first_byte_latency_ms`
- `last_progress_latency_ms`
- `completed`
- `abort_reason`

### 8.3 Optional checkpoint breakdown

If implementation cost is acceptable, include a nested checkpoint list:

```json
{
  "checkpoints": [
    {
      "offset_seconds": 30,
      "has_any_data": false,
      "making_progress": false,
      "completed": false
    }
  ]
}
```

This is valuable for debugging and product output, but it is optional in the first cut if the summary fields above already capture the final state cleanly.

### 8.4 Backward compatibility

Best practice is compatibility-first schema evolution:

- old runs must still validate
- new fields should be additive where possible
- new execution code must not require the presence of old round/window fields

---

## 9. Failure Handling

### 9.1 Request-level outcomes

Possible prompt-level terminal outcomes remain:

- `completed`
- `timeout`
- `transport_error`
- `invalid_response`
- `truncated`
- `canonicalization_error`

Recommended mapping:

- no data by last no-data checkpoint => `timeout`
- total deadline exceeded after partial progress => `timeout`
- HTTP/network failure => `transport_error`
- complete body but dialect parse failure => `invalid_response`
- complete parsed body with `finish_reason=length` => `truncated`

### 9.2 Suite isolation

`SuiteRunner` must remain the final safety boundary:

- any prompt-level transport or parse failure becomes a prompt result
- the suite always produces one prompt result per prompt definition
- no unexpected transport exception may abort the full run loop

### 9.3 Interaction with endpoint retry policy

The current endpoint `retry_policy` should remain low-level and conservative:

- it may still cover immediate transport failures such as `429`, `5xx`, or connect/network errors
- it must not be used to emulate progress checkpoints by re-submitting prompts on ordinary elapsed-time boundaries

In other words:

- progress monitoring is the outer prompt-level control plane
- endpoint retry policy is the inner transport-level error retry plane

---

## 10. Testing Strategy

### 10.1 Unit tests

Add deterministic tests for:

- runtime policy resolution to new fields
- in-flight request snapshot updates on received bytes
- no-data checkpoint behavior
- progress polling behavior
- total deadline abort
- cancellation behavior
- suite isolation after aborted prompts

### 10.2 Transport tests

Use fake connections/responses to simulate:

- zero bytes until abort
- bytes starting before `30s`
- bytes starting between `30s` and `60s`
- long partial response that never completes
- full response just before `120s`
- parseable completed body

### 10.3 CLI and artifact tests

Verify that:

- `run-suite` emits the new runtime policy snapshot
- `show-run --json` exposes the new fields
- comparison/reporting code remains compatible with runs that contain the new attempt metadata

### 10.4 Live validation

Minimum live validation should include:

- one known thinking endpoint
- one known non-thinking endpoint
- confirmation that a prompt with partial progress does not trigger a new request
- confirmation that a silent prompt is aborted without blocking the suite

---

## 11. Implementation Order

Recommended execution order:

1. update design and task documents
2. snapshot current git state before feature work
3. refactor runtime policy and run contracts to the new monitoring semantics
4. implement progress-aware in-flight HTTP transport
5. rework `LiveRunner` to monitor one request instead of re-issuing prompts
6. update CLI, suite, and artifact reporting
7. run focused tests
8. run live validation against one thinking and one non-thinking endpoint
9. update docs with actual shipped behavior
10. commit and push each stage atomically

---

## 12. Acceptance Criteria

The feature is complete only if all of the following are true:

1. A `thinking` endpoint uses a single request with no-data checkpoints at `30s` and `60s`.
2. A `non-thinking` endpoint uses a single request with a no-data checkpoint at `30s`.
3. Once any body data begins arriving, the runtime checks the same request every `10s` rather than re-sending the prompt.
4. Any request still incomplete after `120s` is aborted and the suite proceeds to the next prompt.
5. The live content output cap remains `3000` where supported.
6. Prompt-level failures do not abort the suite.
7. Run artifacts and CLI output expose the new runtime semantics clearly.
8. Focused unit/integration tests, `ruff`, and `mypy` all pass.

---

## Incremental Implementation Notes

- 2026-03-10 P0 landed the new checkpoint/deadline policy fields and progress-oriented attempt fields.
- Legacy runtime fields remain temporarily present as an explicit compatibility bridge so the old executor path can continue to run until the new in-flight monitor path lands.
