# V2 P4 CLI, Live End-to-End, and Operator Guides Implementation Plan

**Goal:** Expose the v2 architecture through a practical CLI, add fixture-backed and profile-config-backed end-to-end tests, and document the operator workflow for both offline and live collection.

**Architecture:** The CLI remains thin over services, but now includes endpoint-profile validation, live run collection, coverage-aware reporting, and explicit protocol-compatibility diagnostics.

**Tech Stack:** Python 3.12+, Typer, pytest

**Status:** Completed on 2026-03-09

**Acceptance Evidence:**
- `uv run pytest -q`
- `uv run ruff check src tests`
- `uv run mypy src`

---

### Task 1: Rebuild CLI inspection commands around v2 contracts

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `tests/test_cli_commands.py`

**Step 1: Write failing CLI tests**

Test intent:
- `validate-prompts` validates v2 prompt contracts
- `validate-endpoints` validates endpoint-profile YAML
- `show-run` prints coverage and protocol compatibility
- `show-profile` prints reasoning-coverage and prompt-weight summaries

Run: `uv run pytest tests/test_cli_commands.py -q`
Expected: FAIL because the current command output assumes the bootstrap artifacts

**Step 2: Implement the inspection commands**

Implementation intent:
- keep output deterministic
- make coverage and protocol findings first-class
- avoid embedding business logic in CLI handlers

**Step 3: Re-run the tests**

Run: `uv run pytest tests/test_cli_commands.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/cli.py tests/test_cli_commands.py
git commit -m "feat: rebuild CLI inspection commands for v2 artifacts"
```

### Task 2: Add fixture-backed and endpoint-profile-backed suite execution commands

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `tests/e2e/test_suite_runner.py`
- Create: `tests/e2e/test_live_endpoint_profiles.py`

**Step 1: Write failing suite-execution tests**

Test intent:
- `run-suite` can execute in fixture mode under the v2 contracts
- `run-suite` can execute in live mode using an endpoint profile without mutating prompt protocol
- prompt failures remain present in the resulting run artifact

Run: `uv run pytest tests/e2e/test_suite_runner.py tests/e2e/test_live_endpoint_profiles.py -q`
Expected: FAIL because the current command surface and run artifact structure are bootstrap-specific

**Step 2: Implement the suite execution command path**

Implementation intent:
- support fixture and live execution through one service path
- surface endpoint-profile id in the artifact
- preserve traces, failures, and coverage in operator-visible output

**Step 3: Re-run the tests**

Run: `uv run pytest tests/e2e/test_suite_runner.py tests/e2e/test_live_endpoint_profiles.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/cli.py tests/e2e/test_suite_runner.py tests/e2e/test_live_endpoint_profiles.py
git commit -m "feat: add v2 fixture and live suite execution commands"
```

### Task 3: Rebuild profile/calibrate/compare commands for coverage-aware output

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `tests/e2e/test_profile_commands.py`

**Step 1: Write failing profile-command tests**

Test intent:
- `build-profile` accepts v2 runs with prompt failures
- `calibrate` emits v2 thresholds with coverage metadata
- `compare` prints answer similarity, reasoning similarity, coverage ratios, missing prompts, and verdict

Run: `uv run pytest tests/e2e/test_profile_commands.py -q`
Expected: FAIL because current command output only prints the bootstrap comparison fields

**Step 2: Implement the commands**

Implementation intent:
- wire commands to v2 services only
- expose protocol compatibility explicitly
- keep JSON output stable for automation

**Step 3: Re-run the tests**

Run: `uv run pytest tests/e2e/test_profile_commands.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/cli.py tests/e2e/test_profile_commands.py
git commit -m "feat: rebuild profile and comparison commands for v2"
```

### Task 4: Add end-to-end golden-flow tests and operator documentation

**Files:**
- Modify: `tests/e2e/test_golden_flow.py`
- Modify: `README.md`
- Modify: `docs/tasks/README.md`

**Step 1: Write failing golden-flow tests**

Test intent:
- validate prompts and endpoint profiles
- execute released suites through fixture mode
- build profiles
- calibrate thresholds
- compare a suspect run
- report protocol compatibility and coverage-aware verdicts

Run: `uv run pytest tests/e2e/test_golden_flow.py -q`
Expected: FAIL because the bootstrap golden path does not include endpoint profiles, traces, or coverage-aware verdicts

**Step 2: Implement the minimal glue and operator docs**

Implementation intent:
- keep the golden flow as the authoritative operator walkthrough
- document live collection with thinking-aware traces
- explain why protocol incompatibility is not the same as identity mismatch

**Step 3: Re-run the full suite**

Run: `uv run pytest -q`
Expected: PASS

Run: `uv run ruff check src tests`
Expected: PASS

Run: `uv run mypy src`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/e2e/test_golden_flow.py README.md docs/tasks/README.md
git commit -m "docs: add v2 operator flow and end-to-end coverage"
```

### Phase exit criteria

P4 is complete only when:

1. the CLI exposes the full v2 workflow
2. fixture-backed end-to-end tests pass
3. live endpoint-profile execution is supported by the same service path
4. docs explain the difference between protocol compatibility and fingerprint similarity
