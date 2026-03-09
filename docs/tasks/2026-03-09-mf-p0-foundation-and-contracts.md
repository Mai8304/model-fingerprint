# P0 Foundation and Contracts Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Initialize the standalone repository, create the Python package skeleton, and define the typed file contracts and schemas that every later phase depends on.

**Architecture:** Start from a minimal Python CLI package with typed contract models and schema validation. Make filesystem paths, artifact names, and JSON schema generation first-class so later prompt-bank, profile, and comparison code build on stable contracts instead of ad hoc dictionaries.

**Tech Stack:** Python 3.12+, Typer, Pydantic v2, PyYAML, jsonschema, pytest, Ruff, mypy

---

### Task 1: Initialize the repository and package skeleton

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/modelfingerprint/__init__.py`
- Create: `src/modelfingerprint/cli.py`
- Create: `tests/test_cli_smoke.py`

**Step 1: Initialize git if needed**

Run: `git init`
Expected: repository initialized in `/Users/zhuangwei/Downloads/coding/modelfingerprint/.git`

**Step 2: Write the failing CLI smoke test**

Test intent:
- importing `modelfingerprint.cli` works
- `python -m modelfingerprint.cli --help` exits `0`

Run: `pytest tests/test_cli_smoke.py -q`
Expected: FAIL because the package and CLI do not exist yet

**Step 3: Add the minimal package and CLI entrypoint**

Implementation intent:
- define project metadata in `pyproject.toml`
- expose a Typer app with one placeholder command group
- keep CLI output deterministic and minimal

**Step 4: Re-run the smoke test**

Run: `pytest tests/test_cli_smoke.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add .gitignore pyproject.toml README.md src/modelfingerprint/__init__.py src/modelfingerprint/cli.py tests/test_cli_smoke.py
git commit -m "chore: initialize model fingerprint project skeleton"
```

### Task 2: Add path resolution and filesystem layout helpers

**Files:**
- Create: `src/modelfingerprint/settings.py`
- Create: `src/modelfingerprint/storage/filesystem.py`
- Create: `tests/test_settings_paths.py`

**Step 1: Write the failing path test**

Test intent:
- resolve repository-root-relative paths for `prompt-bank`, `profiles`, `runs`, and `calibration`
- create missing directories only when explicitly requested

Run: `pytest tests/test_settings_paths.py -q`
Expected: FAIL because settings and filesystem helpers do not exist yet

**Step 2: Implement the minimal path helpers**

Implementation intent:
- centralize path resolution
- avoid scattering path joins across command handlers
- keep all paths explicit and testable

**Step 3: Re-run the path test**

Run: `pytest tests/test_settings_paths.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/settings.py src/modelfingerprint/storage/filesystem.py tests/test_settings_paths.py
git commit -m "feat: add repository path and filesystem helpers"
```

### Task 3: Define typed prompt, run, profile, and calibration contracts

**Files:**
- Create: `src/modelfingerprint/contracts/prompt.py`
- Create: `src/modelfingerprint/contracts/run.py`
- Create: `src/modelfingerprint/contracts/profile.py`
- Create: `src/modelfingerprint/contracts/calibration.py`
- Create: `tests/contracts/test_contract_models.py`

**Step 1: Write failing contract tests**

Test intent:
- valid prompt/run/profile/calibration payloads parse successfully
- invalid family names, suite ids, and missing feature sections are rejected

Run: `pytest tests/contracts/test_contract_models.py -q`
Expected: FAIL because contract models do not exist yet

**Step 2: Implement the Pydantic contract models**

Implementation intent:
- keep suite and artifact contracts explicit
- use enums or literal values for family and verdict names
- model only the fields required by the design

**Step 3: Re-run the contract tests**

Run: `pytest tests/contracts/test_contract_models.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/contracts/prompt.py src/modelfingerprint/contracts/run.py src/modelfingerprint/contracts/profile.py src/modelfingerprint/contracts/calibration.py tests/contracts/test_contract_models.py
git commit -m "feat: add typed artifact contracts"
```

### Task 4: Generate and validate JSON schemas from the typed contracts

**Files:**
- Create: `schemas/prompt.schema.json`
- Create: `schemas/run.schema.json`
- Create: `schemas/profile.schema.json`
- Create: `schemas/calibration.schema.json`
- Create: `src/modelfingerprint/contracts/schema_export.py`
- Create: `tests/contracts/test_json_schemas.py`

**Step 1: Write failing schema tests**

Test intent:
- exported schemas exist on disk
- sample valid payloads pass `jsonschema`
- sample invalid payloads fail validation

Run: `pytest tests/contracts/test_json_schemas.py -q`
Expected: FAIL because schema files and exporter do not exist yet

**Step 2: Implement schema export and checked-in schema files**

Implementation intent:
- generate schemas from the Pydantic models
- keep schema files committed for auditability
- expose a small helper that can refresh them intentionally

**Step 3: Re-run schema tests**

Run: `pytest tests/contracts/test_json_schemas.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add schemas src/modelfingerprint/contracts/schema_export.py tests/contracts/test_json_schemas.py
git commit -m "feat: add artifact json schemas"
```

### Task 5: Add baseline quality gates

**Files:**
- Create: `ruff.toml`
- Create: `mypy.ini`
- Create: `tests/conftest.py`

**Step 1: Add quality tool configuration**

Implementation intent:
- enforce consistent imports, typing, and test discovery
- keep the project lightweight

**Step 2: Run the baseline checks**

Run: `ruff check src tests`
Expected: PASS

Run: `mypy src`
Expected: PASS

Run: `pytest tests/test_cli_smoke.py tests/test_settings_paths.py tests/contracts -q`
Expected: PASS

**Step 3: Commit**

```bash
git add ruff.toml mypy.ini tests/conftest.py
git commit -m "chore: add baseline quality gates"
```
