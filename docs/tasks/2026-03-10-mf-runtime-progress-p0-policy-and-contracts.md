# Runtime Progress P0 Policy and Contracts

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace round/window runtime semantics with single-request progress-monitoring semantics at the contract and resolver level while preserving backward-compatible artifacts.

**Architecture:** Keep capability probing unchanged, but refactor `RuntimePolicySnapshot` and prompt-attempt contracts so the rest of the runtime can describe checkpoint-based monitoring rather than prompt resubmission. Land the schema changes first so transport work has a stable contract target.

**Tech Stack:** Python, Pydantic, JSON schema export, pytest

**Execution Order:** Stage 1 of 4. Must land before transport changes.

---

### Task 1: Add failing tests for the new runtime policy shape

**Files:**
- Modify: `tests/services/test_runtime_policy.py`
- Modify: `tests/contracts/test_json_schemas.py`
- Modify: `tests/test_cli_commands.py`

**Step 1: Write the failing tests**

Add tests that expect:

- `thinking=supported` resolves to:
  - `execution_class="thinking"`
  - `no_data_checkpoints_seconds=[30, 60]`
  - `progress_poll_interval_seconds=10`
  - `total_deadline_seconds=120`
  - `output_token_cap=3000`
- `thinking=accepted_but_ignored` resolves to:
  - `execution_class="non_thinking"`
  - `no_data_checkpoints_seconds=[30]`
- run schemas accept the new runtime policy shape
- prompt attempt summaries accept the new progress metadata fields

**Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py tests/contracts/test_json_schemas.py tests/test_cli_commands.py -q
```

Expected:

- assertions fail because old runtime policy fields are still present
- schema fixtures fail because attempt summaries still use round/window semantics

### Task 2: Refactor runtime policy resolver

**Files:**
- Modify: `src/modelfingerprint/services/runtime_policy.py`
- Modify: `src/modelfingerprint/contracts/_common.py` only if new literals are needed

**Step 1: Replace round/window constants with monitoring constants**

Land code-level constants for:

- `THINKING_NO_DATA_CHECKPOINTS_SECONDS = [30, 60]`
- `NON_THINKING_NO_DATA_CHECKPOINTS_SECONDS = [30]`
- `PROGRESS_POLL_INTERVAL_SECONDS = 10`
- `TOTAL_REQUEST_DEADLINE_SECONDS = 120`
- `LIVE_CONTENT_OUTPUT_TOKEN_CAP = 3000`

**Step 2: Update the resolver output**

Make `resolve_runtime_policy(...)` return the new snapshot semantics:

- policy id/version
- observed thinking probe status
- execution class
- no-data checkpoints
- progress poll interval
- total deadline
- output token cap

### Task 3: Refactor run contracts and schema export

**Files:**
- Modify: `src/modelfingerprint/contracts/run.py`
- Modify: `src/modelfingerprint/contracts/schema_export.py`
- Regenerate: `schemas/run.schema.json`

**Step 1: Update `RuntimePolicySnapshot`**

Replace or deprecate these fields:

- `round_windows_seconds`
- `max_rounds`

Add these fields:

- `no_data_checkpoints_seconds`
- `progress_poll_interval_seconds`
- `total_deadline_seconds`

**Step 2: Update `PromptAttemptSummary`**

Move away from round/window-specific fields and toward monitored-request fields:

- `request_attempt_index`
- `read_timeout_seconds`
- `output_token_cap`
- `status`
- `error_kind`
- `http_status`
- `latency_ms`
- `finish_reason`
- `answer_text_present`
- `reasoning_visible`
- `bytes_received`
- `first_byte_latency_ms`
- `last_progress_latency_ms`
- `completed`
- `abort_reason`

If backward compatibility requires it, make old fields optional rather than deleting them immediately.

### Task 4: Update fixtures and CLI schema expectations

**Files:**
- Modify: `tests/test_cli_commands.py`
- Modify: `tests/contracts/test_json_schemas.py`

**Step 1: Refresh sample artifacts**

Update fixture payloads so `show-run --json` and schema validation expect the new runtime policy and attempt fields.

**Step 2: Run verification**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py tests/contracts/test_json_schemas.py tests/test_cli_commands.py -q
uv run ruff check src tests
uv run mypy src
```

### Task 5: Update docs, commit, and push

**Files:**
- Update: `docs/plans/2026-03-10-single-request-progress-runtime-design.md`
- Update: `docs/tasks/2026-03-10-mf-runtime-progress-p0-policy-and-contracts.md`

**Step 1: Record actual contract deltas**

Document any compatibility concessions that were needed for old runs.

**Step 2: Commit**

Suggested commit:

```bash
git add src/modelfingerprint/services/runtime_policy.py src/modelfingerprint/contracts/run.py src/modelfingerprint/contracts/schema_export.py schemas/run.schema.json tests/services/test_runtime_policy.py tests/contracts/test_json_schemas.py tests/test_cli_commands.py docs/plans/2026-03-10-single-request-progress-runtime-design.md docs/tasks/2026-03-10-mf-runtime-progress-p0-policy-and-contracts.md
git commit -m "feat: refactor runtime policy for progress monitoring"
git push origin main
```

**Acceptance**

- runtime policy exposes checkpoint/deadline semantics instead of round/window semantics
- run contracts validate the new attempt summary shape
- schema export and tests pass

---

## Completion Notes

- Completed on 2026-03-10.
- `RuntimePolicySnapshot` now carries:
  - `no_data_checkpoints_seconds`
  - `progress_poll_interval_seconds`
  - `total_deadline_seconds`
  - `output_token_cap`
- Legacy fields `round_windows_seconds` and `max_rounds` remain temporarily optional to keep the pre-existing executor path working until P2 lands.
- `PromptAttemptSummary` now supports progress-monitoring fields:
  - `request_attempt_index`
  - `bytes_received`
  - `first_byte_latency_ms`
  - `last_progress_latency_ms`
  - `completed`
  - `abort_reason`
- Verification used:
  - `uv run python -c 'from modelfingerprint.contracts.schema_export import export_schemas; export_schemas()'`
  - `uv run pytest tests/services/test_runtime_policy.py tests/contracts/test_json_schemas.py tests/test_cli_commands.py -q`
  - `uv run ruff check src tests`
  - `uv run mypy src`
