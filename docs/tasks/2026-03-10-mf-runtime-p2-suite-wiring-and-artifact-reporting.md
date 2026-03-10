# Runtime P2 Suite Wiring and Artifact Reporting

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire runtime policy resolution into CLI and suite execution, guarantee prompt-level isolation across the suite, and expose the new runtime metadata through artifacts and operator-facing commands.

**Architecture:** CLI remains the entry point for live runs, but it now becomes responsible for passing probe output through the runtime-policy resolver into `LiveRunner`. `SuiteRunner` becomes the final safety boundary that guarantees one prompt result per prompt. Run reporting surfaces the new runtime metadata.

**Tech Stack:** Python, Typer, pytest

**Execution Order:** Stage 3 of 4. Depends on P0 and P1.

---

### Task 1: Add failing CLI and suite tests

**Files:**
- Modify: `tests/e2e/test_suite_runner.py`
- Modify: `tests/test_cli_commands.py`
- Modify: `tests/e2e/test_golden_flow.py` if live-run wiring assertions are needed

**Step 1: Write failing tests**

Cover:

- `run-suite` resolves runtime policy from capability probe output
- `SuiteRunner` keeps running after one prompt returns timeout or transport failure
- serialized run artifacts include:
  - `runtime_policy`
  - prompt-level `attempts`
- operator output remains stable

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/e2e/test_suite_runner.py tests/test_cli_commands.py tests/e2e/test_golden_flow.py -q
```

Expected:

- CLI does not yet pass resolved runtime policy into the transport
- suite isolation assertions fail or missing fields cause assertions to fail

### Task 2: Wire runtime policy through CLI and suite execution

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `src/modelfingerprint/services/suite_runner.py`

**Step 1: Resolve runtime policy in CLI**

After probing capabilities:

- call the new resolver
- pass the resolved policy into `LiveRunner`

**Step 2: Harden suite isolation**

Ensure `SuiteRunner` or `_execute_prompt()` catches broad transport/runtime failures and converts them into prompt results instead of aborting the suite loop.

### Task 3: Expose runtime metadata in run reporting

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `tests/test_cli_commands.py`

**Step 1: Update `show-run`**

Add output for:

- runtime execution class
- runtime output token cap
- maybe attempt counts per prompt if it fits current CLI style

**Step 2: Keep machine-readable output stable**

`show-run --json` should serialize the new fields without special handling from operators.

### Task 4: Verify the full stage

**Files:**
- Modify any affected tests

**Step 1: Run verification**

Run:

```bash
uv run pytest tests/e2e/test_suite_runner.py tests/test_cli_commands.py tests/e2e/test_golden_flow.py -q
uv run ruff check src tests
uv run mypy src
```

Expected:

- CLI and suite runner are wired through the runtime policy path
- one prompt failure no longer aborts the suite
- run artifacts contain runtime execution metadata

### Task 5: Update docs, commit, and push

**Files:**
- Update: `docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md`
- Update: `docs/tasks/2026-03-10-mf-runtime-p2-suite-wiring-and-artifact-reporting.md`

**Step 1: Record interface changes**

Document the final CLI behavior and any run-artifact field names that differ from the initial design.

**Step 2: Commit**

Suggested commit:

```bash
git add src/modelfingerprint/cli.py src/modelfingerprint/services/suite_runner.py tests/e2e/test_suite_runner.py tests/test_cli_commands.py tests/e2e/test_golden_flow.py docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md docs/tasks/2026-03-10-mf-runtime-p2-suite-wiring-and-artifact-reporting.md
git commit -m "feat: wire runtime policy through suite execution"
git push origin main
```

**Acceptance**

- CLI resolves runtime policy from capability probe output
- suite execution is prompt-isolated
- run reporting exposes runtime metadata
- focused e2e/CLI tests, ruff, and mypy pass

