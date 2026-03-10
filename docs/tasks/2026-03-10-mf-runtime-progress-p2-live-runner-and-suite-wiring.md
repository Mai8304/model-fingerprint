# Runtime Progress P2 Live Runner and Suite Wiring

> Implementation update (2026-03-10):
> The shipped runtime uses a unified `10s` in-flight check interval for both `thinking` and `non-thinking` endpoints and does not abort at a `30s/60s` no-data checkpoint. The request stays alive until completion or the `120s` total deadline.

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rework prompt execution so `LiveRunner` monitors one request per prompt-level attempt, applies no-data checkpoints and progress polling, and always lets the suite continue after prompt failure.

**Architecture:** `LiveRunner` becomes the owner of prompt-level monitoring semantics. It starts one in-flight request, polls its progress at checkpoint boundaries, classifies the final result, and records a monitored attempt summary. `SuiteRunner` remains the final prompt-isolation boundary.

**Tech Stack:** Python, pytest, Typer

**Execution Order:** Stage 3 of 4. Depends on P0 and P1.

---

### Task 1: Add failing live-runner tests for the new state machine

**Files:**
- Modify: `tests/transports/test_live_runner.py`
- Modify: `tests/e2e/test_suite_runner.py`
- Modify: `tests/test_cli_commands.py`

**Step 1: Write the failing tests**

Cover:

- `thinking` uses checkpoints at `30s` and `60s`
- `non-thinking` uses a checkpoint at `30s`
- a prompt with partial data does not trigger a second prompt request
- progress polling occurs every `10s` after data begins
- total deadline `120s` aborts an incomplete request
- silent prompts are skipped and the suite continues
- run artifacts and `show-run --json` reflect the new attempt summary fields

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py tests/test_cli_commands.py -q
```

Expected:

- current live runner still performs per-window prompt attempts
- attempt summaries use the old shape

### Task 2: Rework `LiveRunner` around a single request attempt

**Files:**
- Modify: `src/modelfingerprint/transports/live_runner.py`

**Step 1: Replace prompt resubmission loop**

Implement a monitored-request path that:

- starts one in-flight request
- waits until each no-data checkpoint
- checks:
  - completed parseable response
  - has any data
  - last progress time
- transitions into `10s` polling once data begins

**Step 2: Enforce the total deadline**

Abort the in-flight request if:

- no data exists by the last allowed checkpoint
- or elapsed wall-clock exceeds `120s`

**Step 3: Preserve low-level retry policy correctly**

If low-level transport retry remains in `_send_request` or the worker path, ensure it only applies to immediate transport errors, not elapsed-time checkpoint logic.

### Task 3: Update suite and CLI reporting

**Files:**
- Modify: `src/modelfingerprint/services/suite_runner.py`
- Modify: `src/modelfingerprint/cli.py`

**Step 1: Keep prompt isolation**

Ensure any in-flight transport failure or cancellation still becomes a prompt result and does not escape the suite loop.

**Step 2: Expose the new runtime semantics**

Update human-readable and JSON reporting so operators can see:

- execution class
- no-data checkpoints
- progress poll interval
- total deadline
- prompt attempt summaries with bytes/progress fields

### Task 4: Verify the stage

**Files:**
- Modify any affected tests

**Step 1: Run verification**

Run:

```bash
uv run pytest tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py tests/test_cli_commands.py -q
uv run ruff check src tests
uv run mypy src
```

### Task 5: Update docs, commit, and push

**Files:**
- Update: `docs/plans/2026-03-10-single-request-progress-runtime-design.md`
- Update: `docs/tasks/2026-03-10-mf-runtime-progress-p2-live-runner-and-suite-wiring.md`

**Step 1: Record final state-machine behavior**

Document any practical deviation from the intended checkpoint schedule.

**Step 2: Commit**

Suggested commit:

```bash
git add src/modelfingerprint/transports/live_runner.py src/modelfingerprint/services/suite_runner.py src/modelfingerprint/cli.py tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py tests/test_cli_commands.py docs/plans/2026-03-10-single-request-progress-runtime-design.md docs/tasks/2026-03-10-mf-runtime-progress-p2-live-runner-and-suite-wiring.md
git commit -m "feat: add single-request progress-aware runtime"
git push origin main
```

**Acceptance**

- prompt execution uses one in-flight request rather than repeated prompt submissions
- suite remains prompt-isolated
- reporting exposes the new semantics

---

## Completion Notes

- Completed on 2026-03-10.
- `LiveRunner` runtime-policy path now:
  - starts one in-flight request per prompt
  - checks no-data checkpoints from the resolved policy
  - switches to `10s` polling after the first observed response bytes
  - aborts on no-data timeout or total deadline exhaustion
- Runtime-policy execution no longer re-submits prompts on checkpoint expiry.
- `show-run` now prints:
  - `runtime_no_data_checkpoints`
  - `runtime_progress_poll_interval_seconds`
  - `runtime_total_deadline_seconds`
- Verification used:
  - `uv run pytest tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py tests/test_cli_commands.py tests/transports/test_protocol_invariants.py -q`
  - `uv run ruff check src tests`
  - `uv run mypy src`
