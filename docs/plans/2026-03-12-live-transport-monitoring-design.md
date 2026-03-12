# Live Transport Monitoring Design

**Date**

2026-03-12

**Status**

Approved for planning

**Problem**

The current live execution path applies progress monitoring whenever a runtime policy is present, even when the outbound request is a normal JSON request that expects a single final response body.

That causes a transport mismatch:

- direct HTTP requests to some compatible endpoints succeed
- the CLI live suite fails with `no_data_checkpoint_exceeded`
- the failure is caused by local monitoring policy, not by an upstream protocol error
- the current non-thinking first no-data checkpoint of 30 seconds is too aggressive for true streaming cases

**Goal**

Make live execution choose the transport path based on the actual request mode:

- non-streaming JSON requests should use blocking request execution
- streaming or SSE requests should keep in-flight monitoring
- true streaming no-data checkpoints should be relaxed from 30 seconds to 60 seconds

Then:

- keep current runtime policy serialization and observability fields where they still make sense
- preserve streaming timeout and abort-reason behavior for monitored requests
- restore compatibility for providers that return a final JSON body without intermediate progress bytes

**Non-Goals**

- no change to the total live request deadline of 120 seconds in this phase
- no new endpoint profile fields for transport mode
- no attempt to infer streaming mode from capability probe support alone
- no changes to prompt-bank content, extractor behavior, or comparison logic

**Constraints**

- request execution mode must be derived from the concrete outbound request, not from provider branding
- behavior must stay compatible with current CLI and web API contracts
- the change must avoid touching unrelated user edits already present in the worktree
- deployment must follow the repository's serial server procedure

## Approaches Considered

1. Raise the no-data checkpoint from 30 seconds to 60 seconds everywhere.

This is the smallest patch, but it does not fix the incorrect transport abstraction for non-streaming JSON requests.

2. Route non-streaming JSON requests through blocking execution and keep existing 30-second streaming checkpoints.

This fixes the transport abstraction, but still leaves real streaming requests on an aggressive first-byte deadline.

3. Route non-streaming JSON requests through blocking execution and raise streaming no-data checkpoints to 60 seconds.

This fixes the abstraction error and softens streaming false negatives without changing the overall request budget.

**Recommendation**

Use approach 3.

## Design

### 1. Request Execution Mode

`LiveRunner` should determine request execution mode from the `HttpRequestSpec` that is about to be sent.

The rule is:

- treat the request as `streaming` when either:
  - the `Accept` header contains `text/event-stream`
  - the JSON body contains `stream: true`
- otherwise treat it as `blocking_json`

This decision should be local to `LiveRunner`. It should not be added to endpoint profiles or runtime policy contracts.

### 2. Runtime Policy Semantics

`runtime_policy` should continue to describe deadlines and checkpoint values, but it should no longer implicitly force progress monitoring for every request.

The meaning becomes:

- `blocking_json`
  - use `total_deadline_seconds` as the read timeout budget
  - do not apply no-data checkpoint cancellation
- `streaming`
  - use in-flight monitoring
  - apply no-data checkpoints and progress polling as before

### 3. LiveRunner Execution Flow

When runtime policy is present:

1. build the request
2. classify it as `blocking_json` or `streaming`
3. if `blocking_json`
   - call the existing blocking send path with `read_timeout_seconds=total_deadline_seconds`
   - parse and classify the final payload as usual
4. if `streaming`
   - keep using `_start_request()` and `_monitor_inflight_request()`

This preserves the current parsing and prompt-classification logic while changing only the transport selection step.

### 4. Attempt Metadata

For `blocking_json` requests executed through `send()`:

- keep `latency_ms`
- set `completed=True` on successful completion
- keep `finish_reason`, `answer_text_present`, and `reasoning_visible` when available
- leave byte-progress fields unpopulated or zeroed rather than fabricating progress data

For `streaming` requests:

- preserve existing snapshot-derived fields
- preserve `abort_reason` behavior for timeouts and cancellations

### 5. Updated Checkpoints

The runtime policy constants should change to:

- thinking: `[60, 90]`
- non-thinking: `[60]`

The total deadline remains `120` seconds.

This keeps the checkpoint widening scoped to "no first data observed yet" rather than increasing full-request runtime.

### 6. Testing Strategy

Add or update tests for:

- runtime policy constants and serialized values
- `LiveRunner` choosing `send()` for runtime-policy requests that are plain JSON
- `LiveRunner` continuing to use monitored in-flight execution for true streaming requests
- timeout and abort-reason behavior still working for monitored streaming requests
- CLI and web orchestrator runtime policy assertions updated to the new checkpoint values

### 7. Deployment And Verification

Verification should include:

- targeted pytest coverage for runtime policy and live transport behavior
- a real live `run-suite quick-check-v3` retry against the previously failing endpoint
- server deployment only after local verification succeeds

Server deployment remains:

1. sync workspace to `/home/ubuntu/modelfingerprint`
2. run remote `pnpm build` in `/home/ubuntu/modelfingerprint/apps/web`
3. restart `modelfingerprint-web`
4. smoke-check `https://model-fingerprint.com` and `/api/v1/fingerprints`
