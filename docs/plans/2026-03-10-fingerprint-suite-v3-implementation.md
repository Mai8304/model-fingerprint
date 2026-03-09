# Fingerprint Suite V3 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `fingerprint-suite-v3`, a 5-prompt high-density suite that preserves the existing minimal capability probes, introduces safe tolerant JSON canonicalization, and enables side-by-side comparison against `fingerprint-suite-v2`.

**Architecture:** Keep the capability dimension unchanged. Add five new prompt definitions and a new suite, implement a tolerant JSON canonicalizer that only repairs format, add prompt-specific scorers and surface features for parse-repair behavior, then validate v3 against v2 with profile/calibration rebuilds and cross-model comparisons.

**Tech Stack:** Python 3.12+, Pydantic v2, Typer, pytest, Ruff, mypy, YAML prompt-bank definitions

---

### Task 1: Add prompt-bank tests for the new v3 suite shape

**Files:**
- Modify: `tests/prompt_bank/test_loaders.py`
- Modify: `tests/prompt_bank/test_release_suites.py`

**Step 1: Write the failing test**

Add tests asserting:
- `fingerprint-suite-v3.yaml` loads successfully
- it contains exactly `p021` through `p025`
- it coexists with v1 and v2 without breaking subset validation rules

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/prompt_bank/test_loaders.py tests/prompt_bank/test_release_suites.py -q`
Expected: FAIL because the v3 suite file does not exist yet

**Step 3: Write minimal implementation**

Create `prompt-bank/suites/fingerprint-suite-v3.yaml` and, if needed, `prompt-bank/suites/quick-check-v3.yaml` with the correct prompt ids and metadata.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/prompt_bank/test_loaders.py tests/prompt_bank/test_release_suites.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/prompt_bank/test_loaders.py tests/prompt_bank/test_release_suites.py prompt-bank/suites/fingerprint-suite-v3.yaml prompt-bank/suites/quick-check-v3.yaml
git commit -m "test: add v3 suite definitions"
```

### Task 2: Add safe tolerant-JSON canonicalization tests

**Files:**
- Modify: `tests/canonicalizers/test_registry.py`
- Create: `tests/canonicalizers/test_tolerant_json.py`

**Step 1: Write the failing test**

Add tests for a new tolerant JSON canonicalizer that:
- strips markdown fences
- removes leading or trailing explanatory text
- extracts the first complete JSON object
- normalizes approved key aliases
- rejects outputs that would require semantic guessing

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/canonicalizers/test_registry.py tests/canonicalizers/test_tolerant_json.py -q`
Expected: FAIL because the tolerant canonicalizer does not exist yet

**Step 3: Write minimal implementation**

Create a new canonicalizer module and register it in:
- `src/modelfingerprint/canonicalizers/registry.py`
- supporting helpers under `src/modelfingerprint/canonicalizers/`

Keep repairs strictly format-only.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/canonicalizers/test_registry.py tests/canonicalizers/test_tolerant_json.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/canonicalizers/test_registry.py tests/canonicalizers/test_tolerant_json.py src/modelfingerprint/canonicalizers
git commit -m "feat: add tolerant json canonicalization for v3"
```

### Task 3: Add the five new prompt definitions

**Files:**
- Create: `prompt-bank/candidates/p021.yaml`
- Create: `prompt-bank/candidates/p022.yaml`
- Create: `prompt-bank/candidates/p023.yaml`
- Create: `prompt-bank/candidates/p024.yaml`
- Create: `prompt-bank/candidates/p025.yaml`
- Modify: `tests/prompt_bank/test_prompt_bank_contracts.py`

**Step 1: Write the failing test**

Add prompt-bank contract tests asserting:
- all five new prompts validate
- each prompt uses the shared top-level JSON contract
- each prompt declares the correct family and extractors

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/prompt_bank/test_prompt_bank_contracts.py -q`
Expected: FAIL because the prompts do not exist yet

**Step 3: Write minimal implementation**

Create the five YAML definitions with:
- high-density evidence blocks
- shared top-level JSON fields
- family-specific scoring extractors
- prompt weights

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/prompt_bank/test_prompt_bank_contracts.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/prompt_bank/test_prompt_bank_contracts.py prompt-bank/candidates/p021.yaml prompt-bank/candidates/p022.yaml prompt-bank/candidates/p023.yaml prompt-bank/candidates/p024.yaml prompt-bank/candidates/p025.yaml
git commit -m "feat: add v3 high-density prompt definitions"
```

### Task 4: Add prompt-specific v3 scorer tests

**Files:**
- Modify: `tests/extractors/test_v2_probe_extractors.py`
- Create: `tests/extractors/test_v3_probe_extractors.py`

**Step 1: Write the failing test**

Add scorer tests covering:
- grounding with outdated fact rejection
- retrieval with current-validity filtering and paragraph mapping
- abstention with `answer` vs `unknown` vs `conflict_unresolved`
- state tracking with defaults and exceptions
- representation alignment with ambiguous abbreviation preservation

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/extractors/test_v3_probe_extractors.py -q`
Expected: FAIL because the v3 scorer logic does not exist yet

**Step 3: Write minimal implementation**

Implement or extend family extractors under:
- `src/modelfingerprint/extractors/`
- `src/modelfingerprint/extractors/registry.py`

Prefer extending existing family modules over creating duplicate families when possible.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/extractors/test_v3_probe_extractors.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/extractors/test_v3_probe_extractors.py src/modelfingerprint/extractors src/modelfingerprint/extractors/registry.py
git commit -m "feat: add v3 scorer coverage"
```

### Task 5: Add v3 surface features for parse repair behavior

**Files:**
- Modify: `src/modelfingerprint/extractors/surface.py`
- Modify: `src/modelfingerprint/services/feature_pipeline.py`
- Modify: `tests/extractors/test_surface.py`

**Step 1: Write the failing test**

Add tests asserting the pipeline records:
- whether safe repair happened
- how many repair events occurred
- whether extra prefix/suffix text existed
- whether key aliases were normalized

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/extractors/test_surface.py -q`
Expected: FAIL because those surface features are not exposed yet

**Step 3: Write minimal implementation**

Update surface extraction and pipeline wiring so canonicalization events can contribute v3 surface features without changing semantic scoring.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/extractors/test_surface.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/extractors/test_surface.py src/modelfingerprint/extractors/surface.py src/modelfingerprint/services/feature_pipeline.py
git commit -m "feat: score parse repair as surface signal"
```

### Task 6: Wire v3 into CLI and suite-loading flows

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `tests/test_cli_commands.py`
- Modify: `tests/e2e/test_suite_runner.py`

**Step 1: Write the failing test**

Add tests asserting:
- `show-suite fingerprint-suite-v3` works
- `run-suite fingerprint-suite-v3` resolves the five new prompts
- v3 uses the same capability-probe path as v2

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_commands.py tests/e2e/test_suite_runner.py -q`
Expected: FAIL because the suite does not exist yet end-to-end

**Step 3: Write minimal implementation**

Wire suite-loading only where necessary. Avoid adding special-case code if the prompt-bank path already handles v3 naturally.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_commands.py tests/e2e/test_suite_runner.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_cli_commands.py tests/e2e/test_suite_runner.py src/modelfingerprint/cli.py
git commit -m "feat: expose v3 suite through cli"
```

### Task 7: Build a focused v3 fixture set and verify scoring

**Files:**
- Create: `tests/fixtures/fingerprint_suite_v3_responses.json`
- Modify: `tests/e2e/test_profile_commands.py`
- Modify: `tests/e2e/test_golden_flow.py`

**Step 1: Write the failing test**

Add fixture-driven tests that:
- run v3 without live endpoints
- build a v3 profile
- compare a known run against multiple profiles
- ensure tolerant JSON repair does not collapse into false positives

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/e2e/test_profile_commands.py tests/e2e/test_golden_flow.py -q`
Expected: FAIL because the v3 fixture set and compare path do not exist yet

**Step 3: Write minimal implementation**

Add the fixture responses and any minimal fixture-wiring needed for stable offline verification.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/e2e/test_profile_commands.py tests/e2e/test_golden_flow.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/fixtures/fingerprint_suite_v3_responses.json tests/e2e/test_profile_commands.py tests/e2e/test_golden_flow.py
git commit -m "test: add v3 fixture-driven compare flow"
```

### Task 8: Run focused verification for the v3 implementation

**Files:**
- Modify as needed after failures

**Step 1: Run the focused test suite**

Run: `uv run pytest tests/prompt_bank/test_loaders.py tests/prompt_bank/test_release_suites.py tests/prompt_bank/test_prompt_bank_contracts.py tests/canonicalizers/test_registry.py tests/canonicalizers/test_tolerant_json.py tests/extractors/test_v3_probe_extractors.py tests/extractors/test_surface.py tests/test_cli_commands.py tests/e2e/test_suite_runner.py tests/e2e/test_profile_commands.py tests/e2e/test_golden_flow.py -q`
Expected: PASS

**Step 2: Run static checks**

Run: `uv run ruff check src tests`
Expected: PASS

Run: `uv run mypy src`
Expected: PASS

### Task 9: Rebuild v3 reference artifacts and compare against v2

**Files:**
- Create: `profiles/fingerprint-suite-v3/*.json`
- Create: `runs/<date>/*fingerprint-suite-v3.json`
- Create: `calibration/fingerprint-suite-v3.json`
- Optionally modify: `docs/plans/2026-03-10-fingerprint-suite-v3-design.md`

**Step 1: Run live smoke set**

Run v3 on at least:
- `glm-5`
- `deepseek-chat`
- one second OpenRouter non-GLM model

Expected:
- v3 produces scoreable runs
- v3 profile/calibration build succeeds

**Step 2: Compare v3 vs v2**

Record:
- end-to-end runtime
- scoreable coverage
- same-model vs cross-model separation
- Top1 and margin quality

**Step 3: Document the outcome**

Update the design doc or add a short validation note with:
- whether v3 is ready to replace v2
- whether it should remain an experimental parallel suite

**Step 4: Commit**

```bash
git add profiles/fingerprint-suite-v3 runs calibration/fingerprint-suite-v3.json docs/plans/2026-03-10-fingerprint-suite-v3-design.md
git commit -m "feat: validate fingerprint suite v3 against v2"
```
