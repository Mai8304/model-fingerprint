# V2 Fingerprint Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a versioned v2 fingerprint suite with 10 new prompts, a correctness-scoring channel, and updated profile/comparison logic that separates task quality, behavior features, and capability evidence.

**Architecture:** Keep `fingerprint-suite-v1` intact and introduce a parallel v2 protocol. Extend prompt contracts with scorer/evaluation metadata, add a new `score.*` feature channel in run artifacts, and update profile/comparison math so v2 runs combine correctness, behavior, transport, reasoning, and surface signals without breaking existing v1 artifacts.

**Tech Stack:** Python 3.12+, Pydantic v2, PyYAML, pytest, Ruff, mypy

---

### Task 1: Add v2 prompt and scoring contracts

**Files:**
- Modify: `src/modelfingerprint/contracts/_common.py`
- Modify: `src/modelfingerprint/contracts/prompt.py`
- Modify: `src/modelfingerprint/contracts/run.py`
- Modify: `tests/contracts/test_contract_models.py`
- Modify: `schemas/prompt.schema.json`
- Modify: `schemas/run.schema.json`

**Step 1: Write the failing contract tests**

Add tests for:
- v2 prompt families
- optional prompt evaluation payloads
- optional prompt score extractor ids
- run artifacts that carry `score.*` features on completed prompts

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/contracts/test_contract_models.py -q`
Expected: FAIL because the v2 fields and families do not exist yet

**Step 3: Implement the minimal contract changes**

Add:
- new prompt families for the redesigned v2 suite
- a prompt evaluation payload for ground-truth/reference data
- a `score` extractor slot alongside answer/reasoning/transport extractors

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/contracts/test_contract_models.py -q`
Expected: PASS

### Task 2: Add correctness scorers and a new `score.*` pipeline channel

**Files:**
- Modify: `src/modelfingerprint/extractors/base.py`
- Modify: `src/modelfingerprint/extractors/registry.py`
- Modify: `src/modelfingerprint/services/feature_pipeline.py`
- Modify: `src/modelfingerprint/services/profile_builder.py`
- Modify: `src/modelfingerprint/services/calibrator.py`
- Modify: `tests/extractors/test_registry.py`
- Modify: `tests/run/test_feature_pipeline.py`
- Modify: `tests/profile/test_profile_builder.py`
- Modify: `tests/comparison/test_comparator.py`
- Create: `src/modelfingerprint/extractors/evidence_grounding.py`
- Create: `src/modelfingerprint/extractors/context_retrieval.py`
- Create: `src/modelfingerprint/extractors/abstention.py`
- Create: `src/modelfingerprint/extractors/state_tracking.py`
- Create: `src/modelfingerprint/extractors/representation_alignment.py`
- Create: `extractors/evidence_grounding_v1.yaml`
- Create: `extractors/context_retrieval_v1.yaml`
- Create: `extractors/abstention_v1.yaml`
- Create: `extractors/state_tracking_v1.yaml`
- Create: `extractors/representation_alignment_v1.yaml`

**Step 1: Write the failing tests**

Add tests for:
- registry resolution of score extractors
- run artifacts that emit `score.*`, `answer.*`, `transport.*`, `reasoning.*`, `surface.*`
- profile aggregation that preserves score feature summaries
- comparison weighting that includes the score channel

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/extractors/test_registry.py tests/run/test_feature_pipeline.py tests/profile/test_profile_builder.py tests/comparison/test_comparator.py -q`
Expected: FAIL because score-channel extraction is not implemented

**Step 3: Implement the minimal scoring pipeline**

Add:
- score extractor support in the registry
- score feature extraction in the run pipeline
- channel weighting updates in comparison/calibration
- capability-presence features through transport/score channels

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/extractors/test_registry.py tests/run/test_feature_pipeline.py tests/profile/test_profile_builder.py tests/comparison/test_comparator.py -q`
Expected: PASS

### Task 3: Add the v2 prompt bank and candidate validation

**Files:**
- Modify: `src/modelfingerprint/services/prompt_bank.py`
- Modify: `tests/prompt_bank/test_candidate_files.py`
- Modify: `tests/prompt_bank/test_suite_loader.py`
- Create: `prompt-bank/candidates/p011.yaml`
- Create: `prompt-bank/candidates/p012.yaml`
- Create: `prompt-bank/candidates/p013.yaml`
- Create: `prompt-bank/candidates/p014.yaml`
- Create: `prompt-bank/candidates/p015.yaml`
- Create: `prompt-bank/candidates/p016.yaml`
- Create: `prompt-bank/candidates/p017.yaml`
- Create: `prompt-bank/candidates/p018.yaml`
- Create: `prompt-bank/candidates/p019.yaml`
- Create: `prompt-bank/candidates/p020.yaml`
- Create: `prompt-bank/suites/fingerprint-suite-v2.yaml`
- Create: `prompt-bank/suites/quick-check-v2.yaml`

**Step 1: Write the failing prompt-bank tests**

Add tests for:
- presence of the 10 new v2 prompts
- v2 suite references only v2 prompt ids
- quick-check-v2 remains a strict subset of fingerprint-suite-v2
- every v2 prompt carries score extractors and evaluation payloads

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/prompt_bank/test_candidate_files.py tests/prompt_bank/test_suite_loader.py -q`
Expected: FAIL because the v2 suite and prompts do not exist yet

**Step 3: Implement the v2 prompt-bank files**

Seed:
- 2 `evidence_grounding` prompts
- 2 `context_retrieval` prompts
- 2 `abstention` prompts
- 2 `state_tracking` prompts
- 2 `representation_alignment` prompts

**Step 4: Re-run tests to verify they pass**

Run: `uv run pytest tests/prompt_bank/test_candidate_files.py tests/prompt_bank/test_suite_loader.py -q`
Expected: PASS

### Task 4: Verify the full refreshed flow

**Files:**
- Modify as needed after the targeted tests are green

**Step 1: Run the focused suite**

Run: `uv run pytest tests/contracts/test_contract_models.py tests/extractors/test_registry.py tests/run/test_feature_pipeline.py tests/profile/test_profile_builder.py tests/comparison/test_comparator.py tests/prompt_bank/test_candidate_files.py tests/prompt_bank/test_suite_loader.py -q`
Expected: PASS

**Step 2: Run static validation**

Run: `uv run ruff check src tests`
Expected: PASS

Run: `uv run mypy src`
Expected: PASS
