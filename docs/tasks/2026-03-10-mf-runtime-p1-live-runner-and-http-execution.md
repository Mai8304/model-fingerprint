# Runtime P1 Live Runner and HTTP Execution

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current endpoint-driven thinking fallback path with a policy-driven round/window execution loop in `LiveRunner`, including the fixed `3000` output token cap and prompt-attempt recording.

**Architecture:** `LiveRunner` should accept a resolved runtime policy and execute prompt attempts in rounds. Each window is a real HTTP attempt using the current request/response transport. The HTTP client remains request/response based, but the live runner becomes the owner of prompt-level retry, timeout, and attempt metadata.

**Tech Stack:** Python, Pydantic, pytest

**Execution Order:** Stage 2 of 4. Depends on P0.

---

### Task 1: Add failing transport tests for round/window execution

**Files:**
- Modify: `tests/transports/test_live_runner.py`
- Modify: `tests/transports/test_protocol_invariants.py`

**Step 1: Write failing tests**

Add coverage for:

- `thinking` policy uses two windows per round
- `non-thinking` policy uses one window per round
- at most two rounds are executed
- live content prompts use output token cap `3000`
- prompt-attempt summaries are recorded in returned results
- truncated or empty-answer completions consume the next window
- malformed but non-empty responses stop without infinite retries

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/transports/test_live_runner.py tests/transports/test_protocol_invariants.py -q
```

Expected:

- current live runner does not understand the new runtime policy
- request budget and retry schedule assertions fail

### Task 2: Refactor `LiveRunner` to use runtime policy

**Files:**
- Modify: `src/modelfingerprint/transports/live_runner.py`
- Modify: `src/modelfingerprint/dialects/openai_chat.py`

**Step 1: Add runtime-policy input to `LiveRunner`**

Change construction so the live runner can receive a resolved runtime policy object.

**Step 2: Implement round/window execution**

Implement the nested loop:

- for each round up to `max_rounds`
- for each window timeout in `round_windows_seconds`
- execute one HTTP attempt
- classify result
- either stop or continue

**Step 3: Apply fixed output budget**

When the endpoint supports output caps:

- force live content requests to use `3000`

Capability probes are out of scope for this logic.

**Step 4: Record prompt-attempt summaries**

For each window attempt, record:

- timing
- timeout used
- status/error
- finish reason
- answer presence
- reasoning visibility

### Task 3: Harden transport error capture

**Files:**
- Modify: `src/modelfingerprint/transports/http_client.py`
- Modify: `src/modelfingerprint/transports/live_runner.py`

**Step 1: Normalize transport errors**

Ensure the HTTP client keeps translating:

- timeout
- network
- HTTP status
- invalid JSON

into deterministic Python exceptions.

**Step 2: Prevent prompt-level crashes**

`LiveRunner.execute()` must return a prompt result instead of raising for:

- transport failures
- parse failures
- unexpected response-shape errors

Only truly unrecoverable programmer bugs should escape.

### Task 4: Verify and capture traces

**Files:**
- Modify: `tests/transports/test_live_runner.py`
- Modify: `tests/transports/test_openai_chat_dialect.py` if request assertions need updates

**Step 1: Run verification**

Run:

```bash
uv run pytest tests/transports/test_live_runner.py tests/transports/test_protocol_invariants.py tests/transports/test_openai_chat_dialect.py -q
uv run ruff check src tests
uv run mypy src
```

Expected:

- live runner uses the policy-driven loop
- output budget is fixed to `3000`
- no prompt-level exception path remains untested

### Task 5: Update docs, commit, and push

**Files:**
- Update: `docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md`
- Update: `docs/tasks/2026-03-10-mf-runtime-p1-live-runner-and-http-execution.md`

**Step 1: Record transport behavior that actually shipped**

Document:

- whether legacy endpoint `thinking_policy` remains unused or partially used
- the final definition of retryable prompt outcomes

**Step 2: Commit**

Suggested commit:

```bash
git add src/modelfingerprint/transports/live_runner.py src/modelfingerprint/transports/http_client.py src/modelfingerprint/dialects/openai_chat.py tests/transports/test_live_runner.py tests/transports/test_protocol_invariants.py tests/transports/test_openai_chat_dialect.py docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md docs/tasks/2026-03-10-mf-runtime-p1-live-runner-and-http-execution.md
git commit -m "feat: add thinking-aware live runner execution"
git push origin main
```

**Acceptance**

- live runner follows runtime policy windows and rounds
- live content prompts request `3000` output tokens
- prompt attempts are captured in results
- focused transport tests, ruff, and mypy pass

