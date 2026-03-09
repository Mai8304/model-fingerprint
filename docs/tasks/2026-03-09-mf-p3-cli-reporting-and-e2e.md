# P3 CLI, Reporting, and End-to-End Flows Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose the protocol and comparison workflow through a practical CLI, generate human-readable reports, and add end-to-end tests that prove the tool works from prompt-bank files to final verdict output.

**Architecture:** Add thin CLI commands over the already-tested services instead of embedding business logic in the command handlers. Use fixture-backed end-to-end tests first, then optionally add a pluggable transport adapter for real upstream calls without making live network calls part of the default test path.

**Tech Stack:** Python 3.12+, Typer, pytest

---

### Task 1: Add the prompt-bank and artifact inspection commands

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Create: `tests/test_cli_commands.py`

**Step 1: Write failing CLI command tests**

Test intent:
- `validate-prompts`
- `show-suite`
- `show-run`
- `show-profile`

Run: `pytest tests/test_cli_commands.py -q`
Expected: FAIL because the commands do not exist yet

**Step 2: Implement the inspection commands**

Implementation intent:
- keep handlers thin
- render deterministic text and JSON output
- fail loudly on invalid paths or suite ids

**Step 3: Re-run the CLI command tests**

Run: `pytest tests/test_cli_commands.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/cli.py tests/test_cli_commands.py
git commit -m "feat: add prompt bank and artifact inspection commands"
```

### Task 2: Add the suite-runner command and transport adapter boundary

**Files:**
- Create: `src/modelfingerprint/adapters/openai_chat.py`
- Create: `src/modelfingerprint/services/suite_runner.py`
- Modify: `src/modelfingerprint/cli.py`
- Create: `tests/e2e/test_suite_runner.py`

**Step 1: Write failing suite-runner tests**

Test intent:
- execute a suite through a fake transport adapter
- persist a valid run artifact
- keep transport details outside the scoring code

Run: `pytest tests/e2e/test_suite_runner.py -q`
Expected: FAIL because runner and adapter boundary do not exist yet

**Step 2: Implement the runner and adapter boundary**

Implementation intent:
- pass prompts through a single chat-completion style adapter interface
- keep real network integration optional
- default tests should use fixtures or fakes only

**Step 3: Re-run the suite-runner tests**

Run: `pytest tests/e2e/test_suite_runner.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/adapters/openai_chat.py src/modelfingerprint/services/suite_runner.py src/modelfingerprint/cli.py tests/e2e/test_suite_runner.py
git commit -m "feat: add suite runner and transport boundary"
```

### Task 3: Add `build-profile`, `calibrate`, and `compare` commands

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Create: `tests/e2e/test_profile_commands.py`

**Step 1: Write failing profile and comparison command tests**

Test intent:
- build a profile from fixture runs
- calibrate a suite from fixture baseline runs
- compare a suspect run to known profiles and print structured results

Run: `pytest tests/e2e/test_profile_commands.py -q`
Expected: FAIL because these commands do not exist yet

**Step 2: Implement the commands**

Implementation intent:
- wire commands to services from earlier phases
- support both human-readable and JSON output
- include `top1`, `top2`, `margin`, `claimed_model_similarity`, `consistency`, and `verdict`

**Step 3: Re-run the command tests**

Run: `pytest tests/e2e/test_profile_commands.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/cli.py tests/e2e/test_profile_commands.py
git commit -m "feat: add profile, calibrate, and compare commands"
```

### Task 4: Add end-to-end golden-flow tests and operator docs

**Files:**
- Create: `tests/e2e/test_golden_flow.py`
- Modify: `README.md`
- Create: `docs/plans/README.md`
- Create: `docs/tasks/README.md`

**Step 1: Write the failing end-to-end golden-flow test**

Test intent:
- validate prompt bank
- execute screening suite against fixtures
- build profiles
- calibrate thresholds
- compare a suspect run and get a deterministic verdict

Run: `pytest tests/e2e/test_golden_flow.py -q`
Expected: FAIL because the full flow is not wired yet

**Step 2: Implement the minimal glue needed for the golden path**

Implementation intent:
- keep the test file as the authoritative operator walkthrough
- document every CLI step in `README.md`

**Step 3: Re-run the golden-flow test and full suite**

Run: `pytest -q`
Expected: PASS

Run: `ruff check src tests`
Expected: PASS

Run: `mypy src`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/e2e/test_golden_flow.py README.md docs/plans/README.md docs/tasks/README.md
git commit -m "docs: add operator flow and end-to-end golden path"
```
