# Runtime P0 Policy Resolution and Contracts

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the code-level runtime policy resolver, persist runtime policy snapshots and prompt-attempt summaries in run artifacts, and update schemas/tests before transport behavior changes.

**Architecture:** Introduce a dedicated runtime-policy module that converts minimal capability-probe output into a deterministic execution policy. Extend run contracts first so later transport work has a stable place to record resolved policy and attempt metadata without breaking old artifacts.

**Tech Stack:** Python, Pydantic, JSON schema export, pytest

**Execution Order:** Stage 1 of 4. Must land before transport execution changes.

---

### Task 1: Add failing contract and policy tests

**Files:**
- Create: `tests/services/test_runtime_policy.py`
- Modify: `tests/contracts/test_json_schemas.py`
- Modify: `tests/test_cli_commands.py`

**Step 1: Write the failing tests**

- Add runtime-policy resolver tests covering:
  - `thinking=supported -> execution_class=thinking`
  - `thinking=accepted_but_ignored -> execution_class=non-thinking`
  - `thinking=insufficient_evidence -> execution_class=non-thinking`
  - fixed live output token cap of `3000`
- Add schema tests expecting new run fields:
  - `runtime_policy`
  - prompt-level `attempts`
- Add CLI or helper tests that confirm `run-suite` can still serialize runs with the new fields.

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py tests/contracts/test_json_schemas.py tests/test_cli_commands.py -q
```

Expected:

- missing module or import errors for runtime-policy code
- run schema validation failures for the new fields

### Task 2: Implement runtime policy module

**Files:**
- Create: `src/modelfingerprint/services/runtime_policy.py`
- Modify: `src/modelfingerprint/contracts/_common.py` if new literals/enums are needed

**Step 1: Add runtime constants**

Implement constants for:

- `LIVE_CONTENT_OUTPUT_TOKEN_CAP = 3000`
- `THINKING_ROUND_WINDOWS_SECONDS = [30, 30]`
- `NON_THINKING_ROUND_WINDOWS_SECONDS = [30]`
- `MAX_PROMPT_ROUNDS = 2`

**Step 2: Add runtime policy models/helpers**

Add code that resolves a capability-probe payload into a small runtime policy object or dataclass containing:

- policy id/version
- observed thinking probe status
- resolved execution class
- round windows
- max rounds
- output token cap

**Step 3: Keep capability probes unchanged**

Do not modify probe request bodies or probe classifications in this stage.

### Task 3: Extend run contracts and schema export

**Files:**
- Modify: `src/modelfingerprint/contracts/run.py`
- Modify: `src/modelfingerprint/contracts/schema_export.py`
- Regenerate: `schemas/run.schema.json`

**Step 1: Add runtime policy snapshot model**

Add a run-level snapshot that stores:

- policy id
- thinking probe status
- execution class
- round windows
- max rounds
- output token cap

**Step 2: Add prompt-attempt summary model**

Add prompt-level attempt summaries that store:

- round index
- window index
- HTTP attempt index
- read timeout seconds
- output token cap
- terminal status
- error kind
- HTTP status
- latency
- finish reason
- answer text present flag
- reasoning visible flag

**Step 3: Preserve backward compatibility**

- Old runs without these fields must still validate.
- New runs must validate against regenerated schemas.

### Task 4: Wire minimal artifact support and verify

**Files:**
- Modify: `src/modelfingerprint/services/suite_runner.py` only if required for temporary construction support
- Modify: `tests/contracts/test_json_schemas.py`
- Modify: `tests/services/test_runtime_policy.py`

**Step 1: Add only the minimum wiring needed for contract validation**

At this stage, it is acceptable for runtime policy fields to be present but not yet populated by live transport.

**Step 2: Run verification**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py tests/contracts/test_json_schemas.py tests/test_cli_commands.py -q
uv run ruff check src tests
uv run mypy src
```

Expected:

- all tests pass
- schema export remains valid

### Task 5: Update docs, commit, and push

**Files:**
- Update: `docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md`
- Update: `docs/tasks/2026-03-10-mf-runtime-p0-policy-resolution-and-contracts.md`

**Step 1: Record implementation notes**

Add a short completion note documenting:

- exact runtime constants landed
- any deviations from the plan

**Step 2: Commit**

Suggested commit:

```bash
git add src/modelfingerprint/services/runtime_policy.py src/modelfingerprint/contracts/run.py src/modelfingerprint/contracts/schema_export.py schemas/run.schema.json tests/services/test_runtime_policy.py tests/contracts/test_json_schemas.py tests/test_cli_commands.py docs/plans/2026-03-10-thinking-aware-runtime-execution-design.md docs/tasks/2026-03-10-mf-runtime-p0-policy-resolution-and-contracts.md
git commit -m "feat: add runtime policy contracts"
git push origin main
```

**Acceptance**

- runtime policy resolver exists in code
- run contract and schema support new runtime fields
- tests, ruff, and mypy pass

