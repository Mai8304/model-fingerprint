# Dual-Dimension Fingerprint Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a minimal capability-probe dimension for `tools`, `thinking`, `streaming`, and `image`, aggregate that probe evidence into profiles, and combine it with the existing v2 prompt-content fingerprint for final model comparison and verdicts.

**Architecture:** Keep capability evidence separate from prompt-content features. Extend run/profile/comparison contracts with explicit capability sections, aggregate capability outcomes into profile distributions, compute a dedicated `capability_similarity`, and gate verdicts on both coverage and hard mismatch rules. Preserve the existing v2 prompt pipeline as the `content_similarity` source.

**Tech Stack:** Python 3.12+, Pydantic v2, Typer, pytest, Ruff, mypy

---

### Task 1: Add capability sections to run, profile, and comparison contracts

**Files:**
- Modify: `src/modelfingerprint/contracts/run.py`
- Modify: `src/modelfingerprint/contracts/profile.py`
- Modify: `src/modelfingerprint/services/comparator.py`
- Modify: `tests/contracts/test_contract_models.py`
- Modify: `tests/comparison/test_comparator.py`

**Step 1: Write the failing tests**

Add tests for:
- run artifacts carrying a `capability_probe` block
- profile artifacts carrying a `capability_profile` block
- comparison results carrying `capability_similarity`, `capability_coverage_ratio`, and `hard_mismatches`

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/contracts/test_contract_models.py tests/comparison/test_comparator.py -q`
Expected: FAIL because the contract fields do not exist yet

**Step 3: Implement the minimal contract changes**

Add:
- a run-level capability probe payload
- a profile-level capability distribution payload
- comparison fields for capability similarity and coverage

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/contracts/test_contract_models.py tests/comparison/test_comparator.py -q`
Expected: PASS

### Task 2: Lock down minimal capability-probe request shapes and outcomes

**Files:**
- Modify: `src/modelfingerprint/services/capability_probe.py`
- Modify: `tests/services/test_capability_probe.py`
- Modify: `tests/test_capability_probe_cli.py`

**Step 1: Write the failing tests**

Add tests that assert:
- thinking probe sends only `model/messages/max_tokens`
- tools probe sends baseline plus `tools/tool_choice`
- streaming probe sends baseline plus `stream: true`
- image probe uses the image route with the minimum required body
- `429/timeout/network` classify as `insufficient_evidence`, not `unsupported`

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/services/test_capability_probe.py tests/test_capability_probe_cli.py -q`
Expected: FAIL because the probe payload and classification rules are not strict enough yet

**Step 3: Implement the minimal probe rules**

Update the probe service so:
- each capability uses the smallest allowed request delta
- forbidden default fields are not sent
- retry policy is limited to one retry on transient failures
- the returned payload includes probe mode, version, and coverage inputs

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/services/test_capability_probe.py tests/test_capability_probe_cli.py -q`
Expected: PASS

### Task 3: Attach capability probe results to suite runs

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `src/modelfingerprint/services/suite_runner.py`
- Modify: `tests/e2e/test_suite_runner.py`
- Modify: `tests/test_cli_commands.py`

**Step 1: Write the failing tests**

Add tests for:
- `run-suite` on live endpoints storing a `capability_probe` section
- suite output preserving prompt runs and probe results together
- opt-out behavior for fixture-based runs where capability probing is unavailable

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/e2e/test_suite_runner.py tests/test_cli_commands.py -q`
Expected: FAIL because run artifacts do not include capability probe data

**Step 3: Implement the minimal run integration**

Add:
- one capability probe pass before the prompt suite on live endpoints
- run artifact enrichment with the returned probe payload
- no prompt-suite behavior changes beyond storing the probe block

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/e2e/test_suite_runner.py tests/test_cli_commands.py -q`
Expected: PASS

### Task 4: Aggregate capability probe evidence into profiles

**Files:**
- Modify: `src/modelfingerprint/services/profile_builder.py`
- Modify: `tests/profile/test_profile_builder.py`

**Step 1: Write the failing tests**

Add tests for:
- stable capability states aggregating into probability distributions
- mixed outcomes across runs producing fractional distributions
- `insufficient_evidence` reducing capability coverage without pretending to be a stable supported/unsupported state

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/profile/test_profile_builder.py -q`
Expected: FAIL because profile aggregation does not know about capability probes

**Step 3: Implement the minimal profile aggregation**

Add:
- capability distribution summaries per capability
- profile-level capability coverage summary
- persistence of probe mode/version where useful for auditability

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/profile/test_profile_builder.py -q`
Expected: PASS

### Task 5: Add capability similarity scoring and hard mismatch logic

**Files:**
- Modify: `src/modelfingerprint/services/calibrator.py`
- Modify: `src/modelfingerprint/services/comparator.py`
- Modify: `src/modelfingerprint/services/verdicts.py`
- Modify: `tests/comparison/test_comparator.py`
- Modify: `tests/comparison/test_protocol_vs_identity.py`

**Step 1: Write the failing tests**

Add tests for:
- `capability_similarity` scoring using the approved weight matrix
- capability coverage lowering verdict confidence without forcing a false mismatch
- hard mismatch on `thinking` and `tools`
- no hard mismatch from `streaming` or `image` alone

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/comparison/test_comparator.py tests/comparison/test_protocol_vs_identity.py -q`
Expected: FAIL because comparison and verdict logic are content-only

**Step 3: Implement the minimal scoring changes**

Add:
- capability similarity calculation
- capability coverage ratio calculation
- overall score composition: `0.7 * content + 0.3 * capability`
- verdict rules for `match`, `suspicious`, `mismatch`, `unknown`, `insufficient_evidence`

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/comparison/test_comparator.py tests/comparison/test_protocol_vs_identity.py -q`
Expected: PASS

### Task 6: Expose the new fields in CLI output and golden-path tests

**Files:**
- Modify: `src/modelfingerprint/cli.py`
- Modify: `tests/e2e/test_golden_flow.py`
- Modify: `tests/e2e/test_profile_commands.py`

**Step 1: Write the failing tests**

Add tests asserting the CLI emits:
- `capability_similarity`
- `content_similarity`
- `capability_coverage_ratio`
- `hard_mismatches`

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/e2e/test_golden_flow.py tests/e2e/test_profile_commands.py -q`
Expected: FAIL because those fields are not printed yet

**Step 3: Implement the minimal CLI/reporting changes**

Update the CLI presentation so dual-dimension results are visible in:
- compare output
- show-run output
- show-profile output where useful

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/e2e/test_golden_flow.py tests/e2e/test_profile_commands.py -q`
Expected: PASS

### Task 7: Run the focused verification set

**Files:**
- Modify as needed after focused failures

**Step 1: Run the focused test suite**

Run: `uv run pytest tests/contracts/test_contract_models.py tests/services/test_capability_probe.py tests/test_capability_probe_cli.py tests/profile/test_profile_builder.py tests/comparison/test_comparator.py tests/comparison/test_protocol_vs_identity.py tests/e2e/test_suite_runner.py tests/e2e/test_golden_flow.py tests/e2e/test_profile_commands.py tests/test_cli_commands.py -q`
Expected: PASS

**Step 2: Run static checks**

Run: `uv run ruff check src tests`
Expected: PASS

Run: `uv run mypy src`
Expected: PASS

### Task 8: Run one live smoke comparison with minimal probes

**Files:**
- No code changes required unless smoke failures expose a defect

**Step 1: Run one known live model**

Run the existing GLM-5 endpoint through:
- `probe-capabilities`
- `run-suite`
- `compare`

Expected:
- capability probe is stored in the run artifact
- comparison output shows separate capability/content values

**Step 2: Record follow-up gaps**

If the live smoke test exposes provider-specific behavior that breaks minimal-probe assumptions, record the gap before broadening endpoint support.
