# V2 P3 Profile, Calibration, and Comparison Implementation Plan

**Goal:** Rebuild profile generation, calibration, and comparison so they are weight-aware, coverage-aware, and protocol-aware.

**Architecture:** Profiles summarize multi-channel prompt features, calibration records both similarity and coverage statistics, and comparison distinguishes fingerprint similarity from protocol incompatibility.

**Tech Stack:** Python 3.12+, pytest

**Status:** Completed on 2026-03-09

**Acceptance Evidence:**
- `uv run pytest tests/profile tests/calibration tests/comparison -q`
- `uv run ruff check src tests`
- `uv run mypy src`

---

### Task 1: Update profile building for multi-channel weighted features

**Files:**
- Modify: `src/modelfingerprint/services/profile_builder.py`
- Modify: `tests/profile/test_profile_builder.py`
- Modify: `tests/fixtures/profile_runs/*.json`

**Step 1: Write failing profile-builder tests**

Test intent:
- profile summaries preserve namespaced answer/reasoning/transport features
- prompt weights are preserved and later consumed by scoring
- coverage stats and reasoning-visibility stats are included in the profile

Run: `uv run pytest tests/profile/test_profile_builder.py -q`
Expected: FAIL because the current profile builder only supports a flat bootstrap feature map

**Step 2: Implement the v2 profile builder**

Implementation intent:
- summarize multi-channel features deterministically
- preserve sample count and prompt weights
- preserve expected reasoning visibility and coverage characteristics

**Step 3: Re-run the tests**

Run: `uv run pytest tests/profile/test_profile_builder.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/profile_builder.py tests/profile/test_profile_builder.py tests/fixtures/profile_runs
git commit -m "feat: rebuild profiles for weighted multi-channel features"
```

### Task 2: Replace similarity scoring with weighted, coverage-aware scoring

**Files:**
- Modify: `src/modelfingerprint/services/calibrator.py`
- Modify: `src/modelfingerprint/services/comparator.py`
- Modify: `tests/calibration/test_calibrator.py`
- Modify: `tests/comparison/test_comparator.py`

**Step 1: Write failing scoring tests**

Test intent:
- prompt weights affect the final similarity score
- low answer coverage triggers `insufficient_evidence`
- missing required reasoning coverage triggers `incompatible_protocol` or `insufficient_evidence`
- protocol failures are reported separately from semantic mismatch

Run: `uv run pytest tests/calibration/test_calibrator.py tests/comparison/test_comparator.py -q`
Expected: FAIL because the current scoring path only averages flat prompt scores

**Step 2: Implement weighted and coverage-aware scoring**

Implementation intent:
- compute answer / reasoning / transport similarities separately
- use prompt weights from released prompts
- emit explicit coverage and compatibility fields
- keep verdict logic transparent and testable

**Step 3: Re-run the tests**

Run: `uv run pytest tests/calibration/test_calibrator.py tests/comparison/test_comparator.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/calibrator.py src/modelfingerprint/services/comparator.py tests/calibration/test_calibrator.py tests/comparison/test_comparator.py
git commit -m "feat: add weighted coverage-aware comparison scoring"
```

### Task 3: Rebuild calibration artifacts for v2 verdicts

**Files:**
- Modify: `src/modelfingerprint/services/calibrator.py`
- Modify: `tests/fixtures/calibration_runs/*.json`
- Modify: `tests/calibration/test_calibrator.py`

**Step 1: Write failing calibration-artifact tests**

Test intent:
- calibration preserves same-model and cross-model similarity stats
- calibration preserves answer and reasoning coverage thresholds
- verdict thresholds support `match`, `suspicious`, `unknown`, `insufficient_evidence`, and `incompatible_protocol`

Run: `uv run pytest tests/calibration/test_calibrator.py -q`
Expected: FAIL because the current calibration artifact does not model those thresholds

**Step 2: Implement the v2 calibration artifact**

Implementation intent:
- keep thresholds explicit and auditable
- avoid hidden heuristics
- preserve suite-level coverage expectations

**Step 3: Re-run the tests**

Run: `uv run pytest tests/calibration/test_calibrator.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/calibrator.py tests/fixtures/calibration_runs tests/calibration/test_calibrator.py
git commit -m "feat: rebuild calibration artifacts for v2 verdicts"
```

### Task 4: Add regression tests for semantically equivalent shapes and hidden reasoning

**Files:**
- Create: `tests/comparison/test_protocol_vs_identity.py`

**Step 1: Write failing regression tests**

Test intent:
- semantically equivalent canonicalized outputs remain close even if their raw JSON shape differs
- hidden reasoning channel does not automatically imply different model identity
- protocol incompatibility is reported explicitly instead of degrading into an identity mismatch

Run: `uv run pytest tests/comparison/test_protocol_vs_identity.py -q`
Expected: FAIL because the current comparison layer does not distinguish those cases explicitly

**Step 2: Implement the missing comparison behavior**

Implementation intent:
- keep protocol compatibility and identity evidence separate
- preserve operator trust in the output

**Step 3: Re-run the tests**

Run: `uv run pytest tests/comparison/test_protocol_vs_identity.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add tests/comparison/test_protocol_vs_identity.py src/modelfingerprint/services/comparator.py src/modelfingerprint/services/calibrator.py
git commit -m "test: cover protocol compatibility versus identity evidence"
```

### Phase exit criteria

P3 is complete only when:

1. similarity is prompt-weighted
2. coverage is explicit and gating
3. protocol incompatibility is not misreported as model mismatch
4. semantically equivalent shapes remain comparable after canonicalization
