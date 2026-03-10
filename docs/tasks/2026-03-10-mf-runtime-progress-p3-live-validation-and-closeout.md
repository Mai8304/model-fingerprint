# Runtime Progress P3 Live Validation and Closeout

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Validate the new single-request progress runtime against real providers, refresh representative artifacts if needed, and close the feature in a documented, tested state.

**Architecture:** Use one known thinking endpoint and one known non-thinking endpoint to validate the monitoring state machine, then update run/profile/comparison-facing docs with the actual observed behavior. This stage is about evidence, not architecture.

**Tech Stack:** Python CLI, pytest, ruff, mypy

**Execution Order:** Stage 4 of 4. Depends on P0-P2.

---

### Task 1: Run focused regression verification

**Files:**
- No new code expected initially

**Step 1: Run the regression suite**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py tests/transports/test_http_client.py tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py tests/test_cli_commands.py -q
uv run ruff check src tests
uv run mypy src
```

### Task 2: Run live smoke on one thinking endpoint

**Files:**
- Output artifacts under `runs/` and `traces/`

**Step 1: Execute a real quick-check or suite run**

Acceptance observations:

- runtime policy resolves to `thinking`
- the prompt is not resubmitted at the `30s` checkpoint
- if bytes begin to arrive, the runtime keeps the same request alive and polls progress
- if a prompt stays incomplete beyond `120s`, it is aborted and the suite continues

### Task 3: Run live smoke on one non-thinking endpoint

**Files:**
- Output artifacts under `runs/` and `traces/`

**Step 1: Execute a real quick-check or suite run**

Acceptance observations:

- runtime policy resolves to `non-thinking`
- silent prompts abort at the `30s` no-data checkpoint
- prompts with ongoing body output continue on the same request instead of being resent

### Task 4: Refresh docs and operator guidance

**Files:**
- Update: `docs/plans/2026-03-10-single-request-progress-runtime-design.md`
- Update: `docs/tasks/2026-03-10-mf-runtime-progress-p3-live-validation-and-closeout.md`
- Update any operator-facing docs if behavior changed materially

**Step 1: Record live evidence**

Document:

- which endpoints were used
- whether progress polling behaved as designed
- any provider-specific deviations

### Task 5: Final commit and push

**Files:**
- Include code/doc changes and any intentionally tracked artifacts

**Step 1: Commit**

Suggested commit:

```bash
git add src tests docs
git commit -m "fix: validate single-request progress runtime"
git push origin main
```

**Acceptance**

- regression tests pass
- live evidence demonstrates the new runtime semantics
- docs describe shipped behavior, not just intended behavior

