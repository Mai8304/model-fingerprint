# Runtime Progress P1 HTTP Client and In-Flight Monitoring

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a progress-aware HTTP transport that supports single-request monitoring, shared progress snapshots, and deterministic cancellation without requiring SSE.

**Architecture:** Extend the transport layer with an in-flight request abstraction. A worker thread performs the blocking stdlib HTTP request while updating shared progress state. The main runtime polls that state without re-sending prompts.

**Tech Stack:** Python stdlib threading, http.client, pytest

**Execution Order:** Stage 2 of 4. Depends on P0.

---

### Task 1: Add failing transport tests for in-flight monitoring

**Files:**
- Modify: `tests/transports/test_http_client.py`
- Modify: `tests/transports/test_protocol_invariants.py`

**Step 1: Write the failing tests**

Cover:

- an in-flight request exposes `bytes_received=0` before data arrives
- snapshots update when chunks arrive
- cancellation stops a long-running request
- a fully received body returns the same parsed payload as the old `send(...)` path
- no-data and total-deadline scenarios can be simulated deterministically

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/transports/test_http_client.py tests/transports/test_protocol_invariants.py -q
```

Expected:

- missing types or methods for in-flight monitoring
- current blocking `send(...)` path cannot satisfy progress snapshot assertions

### Task 2: Add in-flight request abstractions

**Files:**
- Modify: `src/modelfingerprint/transports/http_client.py`
- Modify: `src/modelfingerprint/contracts/run.py` only if shared models are placed there

**Step 1: Add transport progress models**

Introduce code-level models for:

- `HttpProgressSnapshot`
- terminal transport result or equivalent
- request cancellation signal

**Step 2: Add in-flight request handle**

Expose a new interface on `StandardHttpClient` that allows:

- start request
- inspect snapshot
- wait for terminal settlement
- cancel request

Keep the existing `send(...)` method for compatibility if practical.

### Task 3: Implement worker-thread execution

**Files:**
- Modify: `src/modelfingerprint/transports/http_client.py`

**Step 1: Move blocking request/response logic behind the worker**

The worker should:

- connect
- send request
- read the response body incrementally
- update `bytes_received`, `first_byte`, and `last_progress`
- settle into success or `HttpClientError`

**Step 2: Support cancellation**

Cancellation must:

- signal the worker
- close or invalidate the active connection path
- settle promptly with a deterministic transport outcome

### Task 4: Verify the transport stage

**Files:**
- Modify any affected tests

**Step 1: Run verification**

Run:

```bash
uv run pytest tests/transports/test_http_client.py tests/transports/test_protocol_invariants.py tests/transports/test_live_runner.py -q
uv run ruff check src tests
uv run mypy src
```

### Task 5: Update docs, commit, and push

**Files:**
- Update: `docs/plans/2026-03-10-single-request-progress-runtime-design.md`
- Update: `docs/tasks/2026-03-10-mf-runtime-progress-p1-http-client-and-inflight-monitoring.md`

**Step 1: Record transport design details that shipped**

Document:

- whether cancellation is cooperative or connection-forced
- whether the old `send(...)` path remains or delegates internally

**Step 2: Commit**

Suggested commit:

```bash
git add src/modelfingerprint/transports/http_client.py tests/transports/test_http_client.py tests/transports/test_protocol_invariants.py tests/transports/test_live_runner.py docs/plans/2026-03-10-single-request-progress-runtime-design.md docs/tasks/2026-03-10-mf-runtime-progress-p1-http-client-and-inflight-monitoring.md
git commit -m "feat: add in-flight HTTP progress monitoring"
git push origin main
```

**Acceptance**

- transport can observe byte-level progress without re-sending prompts
- cancellation is deterministic
- focused transport tests pass

