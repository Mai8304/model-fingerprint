# P2 Profiles, Calibration, and Comparison Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the file-based run pipeline, canonical profile generation, suite calibration, and comparison engine that produce open-set retrieval results and final verdicts.

**Architecture:** Treat every suite execution as an immutable run artifact. Aggregate repeated canonical runs into suite-specific model profiles, compute thresholds from calibration runs, then compare a target run against all known profiles using structured feature similarity and explicit verdict rules.

**Tech Stack:** Python 3.12+, Pydantic v2, pytest, jsonschema

**Status:** Completed on 2026-03-09

**Acceptance Evidence:**
- `uv run pytest tests/run tests/profile tests/calibration tests/comparison -q`
- `uv run ruff check src tests`
- `uv run mypy src`

---

### Task 1: Implement run artifacts and feature-pipeline persistence

**Files:**
- Create: `src/modelfingerprint/services/run_writer.py`
- Create: `src/modelfingerprint/services/feature_pipeline.py`
- Create: `tests/run/test_feature_pipeline.py`
- Create: `tests/run/test_run_writer.py`

**Step 1: Write failing run-pipeline tests**

Test intent:
- given prompt results and raw outputs, extract features and write a valid run artifact
- run artifacts land under `runs/YYYY-MM-DD/`
- every prompt result includes raw output, usage, and features

Run: `pytest tests/run/test_feature_pipeline.py tests/run/test_run_writer.py -q`
Expected: FAIL because run pipeline services do not exist yet

**Step 2: Implement the feature pipeline and run writer**

Implementation intent:
- keep prompt execution results separate from storage concerns
- validate run payloads before writing them to disk

**Step 3: Re-run the run-pipeline tests**

Run: `pytest tests/run/test_feature_pipeline.py tests/run/test_run_writer.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/run_writer.py src/modelfingerprint/services/feature_pipeline.py tests/run/test_feature_pipeline.py tests/run/test_run_writer.py
git commit -m "feat: add run artifact pipeline"
```

### Task 2: Implement profile building with robust statistics

**Files:**
- Create: `src/modelfingerprint/services/profile_builder.py`
- Create: `tests/profile/test_profile_builder.py`
- Create: `tests/fixtures/profile_runs/`

**Step 1: Write failing profile-builder tests**

Test intent:
- aggregate repeated runs for one model into one profile
- compute median and MAD for numeric features
- compute empirical probabilities for boolean and enum features

Run: `pytest tests/profile/test_profile_builder.py -q`
Expected: FAIL because the profile builder does not exist yet

**Step 2: Implement the profile builder**

Implementation intent:
- group runs by model and suite
- reject mixed-suite aggregation
- preserve prompt weights in the output profile

**Step 3: Re-run the profile-builder tests**

Run: `pytest tests/profile/test_profile_builder.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/profile_builder.py tests/profile/test_profile_builder.py tests/fixtures/profile_runs
git commit -m "feat: add profile builder"
```

### Task 3: Implement calibration artifact generation

**Files:**
- Create: `src/modelfingerprint/services/calibrator.py`
- Create: `tests/calibration/test_calibrator.py`
- Create: `tests/fixtures/calibration_runs/`

**Step 1: Write failing calibration tests**

Test intent:
- compute same-model and cross-model similarity distributions
- derive suite thresholds for match, suspicious, unknown, margin, and consistency
- write a valid calibration artifact

Run: `pytest tests/calibration/test_calibrator.py -q`
Expected: FAIL because the calibrator does not exist yet

**Step 2: Implement the calibrator**

Implementation intent:
- keep threshold derivation explicit and deterministic
- write thresholds to `calibration/<suite>.json`

**Step 3: Re-run the calibration tests**

Run: `pytest tests/calibration/test_calibrator.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/calibrator.py tests/calibration/test_calibrator.py tests/fixtures/calibration_runs
git commit -m "feat: add suite calibration"
```

### Task 4: Implement similarity scoring, Top1/Top2 ranking, and verdict rules

**Files:**
- Create: `src/modelfingerprint/services/comparator.py`
- Create: `src/modelfingerprint/services/verdicts.py`
- Create: `tests/comparison/test_comparator.py`
- Create: `tests/comparison/test_verdicts.py`

**Step 1: Write failing comparison tests**

Test intent:
- score a target run against multiple profiles
- rank profiles by overall similarity
- compute claimed-model similarity and consistency
- emit `match`, `suspicious`, `mismatch`, or `unknown`

Run: `pytest tests/comparison/test_comparator.py tests/comparison/test_verdicts.py -q`
Expected: FAIL because comparator and verdict services do not exist yet

**Step 2: Implement the comparison engine**

Implementation intent:
- compare feature values by type
- aggregate to prompt score then overall score
- produce stable ordering and structured results

**Step 3: Implement verdict rules against calibration thresholds**

Implementation intent:
- keep threshold checks isolated from scoring math
- make verdicts reproducible from artifacts only

**Step 4: Re-run the comparison tests**

Run: `pytest tests/comparison/test_comparator.py tests/comparison/test_verdicts.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/services/comparator.py src/modelfingerprint/services/verdicts.py tests/comparison/test_comparator.py tests/comparison/test_verdicts.py
git commit -m "feat: add comparison and verdict engine"
```
