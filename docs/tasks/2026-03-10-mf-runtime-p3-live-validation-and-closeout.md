# Runtime P3 Live Validation and Closeout

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Validate the new runtime policy against real endpoints, refresh relevant artifacts if needed, update the documentation with observed behavior, and close the feature with a tested and auditable final state.

**Architecture:** Keep code changes minimal in this stage. The purpose is to prove that the implemented policy works with at least one visible-thinking endpoint and one non-thinking endpoint under the normal CLI path, then capture the results in docs and git history.

**Tech Stack:** Python, Typer CLI, pytest, live endpoint runs

**Execution Order:** Stage 4 of 4. Depends on P0, P1, and P2.

---

### Task 1: Run focused automated verification

**Files:**
- No new code required before this verification pass

**Step 1: Run the main automated checks**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py tests/test_cli_commands.py -q
uv run ruff check src tests
uv run mypy src
```

Expected:

- all new runtime-policy code paths are covered

### Task 2: Run live smoke tests

**Files:**
- Regenerate only if intentionally kept: `runs/<date>/*.fingerprint-suite-v3.json`
- Regenerate only if intentionally kept: `traces/<date>/...`

**Step 1: Run one visible-thinking endpoint**

Use a known visible-thinking profile such as the current OpenRouter GLM-5 path.

Validate:

- runtime policy resolves to `thinking`
- each prompt uses up to `[30, 30]` windows per round
- output cap is `3000`
- suite finishes without blocking on one failed prompt

**Step 2: Run one non-thinking endpoint**

Use a known non-thinking profile such as `deepseek-chat`.

Validate:

- runtime policy resolves to `non-thinking`
- each prompt uses `[30]` per round
- retry round behavior works
- suite finishes

### Task 3: Inspect artifacts and compare to expectations

**Files:**
- Inspect: generated run artifacts
- Inspect: generated traces if retained

**Step 1: Confirm runtime policy snapshot**

Verify that run artifacts capture:

- execution class
- round windows
- max rounds
- output token cap

**Step 2: Confirm prompt-attempt summaries**

Verify that prompt results capture:

- attempt count
- final stop reason
- timeout/error metadata

### Task 4: Update docs with observed behavior

**Files:**
- Update: `docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md`
- Update: all four task docs as completed records

**Step 1: Add completion notes**

Record:

- actual live endpoints tested
- any deviations from planned behavior
- any remaining known limitations

### Task 5: Final commit and push

**Files:**
- Include code, tests, docs, and only intentional regenerated artifacts

**Step 1: Commit**

Suggested commit:

```bash
git add src tests docs
git add calibration profiles runs schemas
git commit -m "feat: validate thinking-aware runtime execution"
git push origin main
```

**Acceptance**

- automated verification passes
- at least one thinking and one non-thinking live smoke test complete
- docs are updated with observed outcomes
- final state is committed and pushed

