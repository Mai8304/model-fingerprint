# V2 P0 Contracts and Fixed Protocol Implementation Plan

**Goal:** Replace the bootstrap artifact contracts and prompt schema with v2 contracts that are thinking-aware, coverage-aware, and suitable for immutable released fingerprint protocols.

**Architecture:** Start by making the protocol explicit in data. Every released prompt becomes a self-contained request contract, every prompt execution becomes a typed status-bearing record, and every live run preserves failures as evidence instead of dropping them.

**Tech Stack:** Python 3.12+, Typer, Pydantic v2, PyYAML, jsonschema, pytest, Ruff, mypy

**Status:** Planned

**Acceptance Evidence:**
- `uv run pytest tests/contracts tests/prompt_bank -q`
- `uv run ruff check src tests`
- `uv run mypy src`

---

### Task 1: Replace the prompt-bank contract with full immutable protocol objects

**Files:**
- Modify: `src/modelfingerprint/contracts/prompt.py`
- Modify: `src/modelfingerprint/services/prompt_bank.py`
- Modify: `schemas/prompt.schema.json`
- Modify: `prompt-bank/candidates/*.yaml`
- Modify: `prompt-bank/suites/*.yaml`
- Modify: `tests/prompt_bank/test_candidate_files.py`
- Modify: `tests/prompt_bank/test_suite_loader.py`

**Step 1: Write failing prompt-bank tests**

Test intent:
- prompt definitions require `messages`
- prompt definitions require fixed `generation`
- prompt definitions require `output_contract` and extractor declarations
- released suites reject prompts missing required capabilities or output-contract ids

Run: `uv run pytest tests/prompt_bank -q`
Expected: FAIL because current prompt definitions still use the bootstrap schema

**Step 2: Implement the v2 prompt schema**

Implementation intent:
- replace `template` with explicit `messages`
- freeze prompt-level generation parameters
- add `output_contract`, `extractors`, and `required_capabilities`
- keep released suite ids unchanged unless the prompt composition itself changes

**Step 3: Rewrite the released prompt-bank files**

Implementation intent:
- move all current supplemental live-run context into the prompt definitions
- keep `fingerprint-suite-v1` and `quick-check-v1` as released suites
- make the released suite files the single source of truth for immutable prompt protocol

**Step 4: Re-run the prompt-bank tests**

Run: `uv run pytest tests/prompt_bank -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/contracts/prompt.py src/modelfingerprint/services/prompt_bank.py schemas/prompt.schema.json prompt-bank/candidates prompt-bank/suites tests/prompt_bank
git commit -m "feat: replace prompt bank with fixed v2 protocol definitions"
```

### Task 2: Replace run/profile/calibration contracts with v2 status-bearing artifacts

**Files:**
- Modify: `src/modelfingerprint/contracts/run.py`
- Modify: `src/modelfingerprint/contracts/profile.py`
- Modify: `src/modelfingerprint/contracts/calibration.py`
- Modify: `src/modelfingerprint/contracts/_common.py`
- Modify: `schemas/run.schema.json`
- Modify: `schemas/profile.schema.json`
- Modify: `schemas/calibration.schema.json`
- Modify: `tests/contracts/test_contract_models.py`
- Modify: `tests/contracts/test_json_schemas.py`

**Step 1: Write failing contract tests**

Test intent:
- run artifacts preserve one record per prompt with typed execution status
- prompt execution records can preserve normalized request snapshots, normalized completion payloads, canonicalization events, and typed errors
- usage supports `reasoning_tokens`
- comparison/calibration payloads support coverage and protocol compatibility fields

Run: `uv run pytest tests/contracts -q`
Expected: FAIL because the current models do not capture those fields

**Step 2: Implement v2 artifact contracts**

Implementation intent:
- add normalized request / normalized completion models
- add prompt execution status enum and error taxonomy
- add run-level coverage and protocol-compatibility summaries
- add profile-level reasoning-coverage and weighted prompt summaries
- add calibration-level coverage thresholds and verdict enums

**Step 3: Refresh and validate the schemas**

Run: `uv run pytest tests/contracts/test_json_schemas.py -q`
Expected: PASS

**Step 4: Re-run all contract tests**

Run: `uv run pytest tests/contracts -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/contracts src/modelfingerprint/contracts/_common.py schemas/run.schema.json schemas/profile.schema.json schemas/calibration.schema.json tests/contracts
git commit -m "feat: add v2 thinking-aware artifact contracts"
```

### Task 3: Add endpoint-profile contracts and schemas

**Files:**
- Create: `src/modelfingerprint/contracts/endpoint.py`
- Create: `schemas/endpoint.schema.json`
- Create: `endpoint-profiles/.gitkeep`
- Create: `tests/contracts/test_endpoint_profiles.py`

**Step 1: Write failing endpoint-profile tests**

Test intent:
- endpoint profiles validate dialect id, field-path mapping, timeout policy, and capability flags
- secrets are referenced by env-var name, not embedded literal values
- invalid path specifications and impossible capability combinations are rejected

Run: `uv run pytest tests/contracts/test_endpoint_profiles.py -q`
Expected: FAIL because endpoint-profile contracts do not exist yet

**Step 2: Implement endpoint-profile contracts**

Implementation intent:
- keep endpoint config declarative
- make dialect id explicit
- make request mapping and response mapping explicit
- make capability checks explicit and testable

**Step 3: Re-run the endpoint-profile tests**

Run: `uv run pytest tests/contracts/test_endpoint_profiles.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/contracts/endpoint.py schemas/endpoint.schema.json endpoint-profiles/.gitkeep tests/contracts/test_endpoint_profiles.py
git commit -m "feat: add endpoint profile contracts and schema"
```

### Task 4: Replace fixture models and path helpers to match v2 artifacts

**Files:**
- Modify: `src/modelfingerprint/settings.py`
- Modify: `src/modelfingerprint/storage/filesystem.py`
- Modify: `tests/test_settings_paths.py`
- Modify: `tests/fixtures/**`

**Step 1: Write failing fixture/path tests**

Test intent:
- `traces/` is recognized as a runtime artifact directory
- v2 fixture payloads validate against the new schemas
- filesystem helpers can create run/profile/calibration/trace directories intentionally

Run: `uv run pytest tests/test_settings_paths.py tests/contracts -q`
Expected: FAIL because the bootstrap fixtures and path helpers still assume the v1 layout

**Step 2: Update helpers and fixtures**

Implementation intent:
- formalize `endpoint-profiles/` and `traces/`
- refresh fixtures to the v2 contracts
- avoid hidden path joins in later phases

**Step 3: Re-run the tests**

Run: `uv run pytest tests/test_settings_paths.py tests/contracts -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/settings.py src/modelfingerprint/storage/filesystem.py tests/test_settings_paths.py tests/fixtures
git commit -m "chore: refresh fixtures and filesystem layout for v2"
```

### Phase exit criteria

P0 is complete only when:

1. released prompt definitions are fully self-contained
2. run artifacts preserve prompt-level failures
3. usage supports reasoning tokens
4. endpoint profiles are typed and schema-validated
5. no later phase needs ad hoc prompt supplementation
