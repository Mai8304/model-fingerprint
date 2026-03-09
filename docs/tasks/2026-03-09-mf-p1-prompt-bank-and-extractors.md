# P1 Prompt Bank and Extractors Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the prompt-bank format, versioned suite loading, and the five extractor families that convert raw outputs into structured feature vectors.

**Architecture:** Keep prompt and suite definitions as YAML source files, validate them against typed contracts, and route each prompt to one extractor family and version. Extractors should be pure functions over prompt output and fixture input so they remain deterministic and independently testable.

**Tech Stack:** Python 3.12+, PyYAML, Pydantic v2, jsonschema, pytest

---

### Task 1: Add prompt-bank loaders and suite validation

**Files:**
- Create: `prompt-bank/candidates/.gitkeep`
- Create: `prompt-bank/suites/default-v1.yaml`
- Create: `prompt-bank/suites/screening-v1.yaml`
- Create: `src/modelfingerprint/services/prompt_bank.py`
- Create: `tests/prompt_bank/test_suite_loader.py`

**Step 1: Write failing loader tests**

Test intent:
- load all candidate prompt files from disk
- validate that `screening-v1` is a strict subset of `default-v1`
- reject duplicate prompt ids and unknown extractors

Run: `pytest tests/prompt_bank/test_suite_loader.py -q`
Expected: FAIL because loader and suite files do not exist yet

**Step 2: Implement the prompt-bank loader**

Implementation intent:
- parse YAML files into typed prompt and suite models
- validate subset and uniqueness rules
- keep suite metadata explicit

**Step 3: Re-run the loader tests**

Run: `pytest tests/prompt_bank/test_suite_loader.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add prompt-bank/suites src/modelfingerprint/services/prompt_bank.py tests/prompt_bank/test_suite_loader.py
git commit -m "feat: add prompt bank and suite loader"
```

### Task 2: Implement the extractor registry and shared extractor interfaces

**Files:**
- Create: `extractors/style_brief_v1.yaml`
- Create: `extractors/strict_format_v1.yaml`
- Create: `extractors/minimal_diff_v1.yaml`
- Create: `extractors/structured_extraction_v1.yaml`
- Create: `extractors/retrieval_v1.yaml`
- Create: `src/modelfingerprint/extractors/base.py`
- Create: `src/modelfingerprint/extractors/registry.py`
- Create: `tests/extractors/test_registry.py`

**Step 1: Write failing registry tests**

Test intent:
- resolve extractor names from prompt definitions
- reject unknown family/version pairs
- enforce that extractor outputs are JSON-serializable feature maps

Run: `pytest tests/extractors/test_registry.py -q`
Expected: FAIL because registry and extractor descriptors do not exist yet

**Step 2: Implement the shared extractor interface**

Implementation intent:
- define a minimal extractor protocol
- keep extractor lookup centralized
- separate extractor metadata from extractor code

**Step 3: Re-run the registry tests**

Run: `pytest tests/extractors/test_registry.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add extractors src/modelfingerprint/extractors/base.py src/modelfingerprint/extractors/registry.py tests/extractors/test_registry.py
git commit -m "feat: add extractor registry"
```

### Task 3: Implement `style_brief` and `strict_format` extractors

**Files:**
- Create: `src/modelfingerprint/extractors/style_brief.py`
- Create: `src/modelfingerprint/extractors/strict_format.py`
- Create: `tests/extractors/test_style_brief.py`
- Create: `tests/extractors/test_strict_format.py`
- Create: `tests/fixtures/extractors/style_brief/`
- Create: `tests/fixtures/extractors/strict_format/`

**Step 1: Write failing fixture-backed tests**

Test intent:
- `style_brief` extracts stable style features from short responses
- `strict_format` detects valid format, field-order obedience, and extra text

Run: `pytest tests/extractors/test_style_brief.py tests/extractors/test_strict_format.py -q`
Expected: FAIL because extractor implementations do not exist yet

**Step 2: Implement the minimal extractor logic**

Implementation intent:
- keep features deterministic
- normalize whitespace consistently
- avoid any model-dependent hidden heuristics

**Step 3: Re-run the extractor tests**

Run: `pytest tests/extractors/test_style_brief.py tests/extractors/test_strict_format.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/extractors/style_brief.py src/modelfingerprint/extractors/strict_format.py tests/extractors/test_style_brief.py tests/extractors/test_strict_format.py tests/fixtures/extractors/style_brief tests/fixtures/extractors/strict_format
git commit -m "feat: add style and strict-format extractors"
```

### Task 4: Implement `minimal_diff` and `structured_extraction` extractors

**Files:**
- Create: `src/modelfingerprint/extractors/minimal_diff.py`
- Create: `src/modelfingerprint/extractors/structured_extraction.py`
- Create: `tests/extractors/test_minimal_diff.py`
- Create: `tests/extractors/test_structured_extraction.py`
- Create: `tests/fixtures/extractors/minimal_diff/`
- Create: `tests/fixtures/extractors/structured_extraction/`

**Step 1: Write failing fixture-backed tests**

Test intent:
- `minimal_diff` scores minimality, reorder tendency, and change span
- `structured_extraction` scores grounded extraction and hallucinated fields

Run: `pytest tests/extractors/test_minimal_diff.py tests/extractors/test_structured_extraction.py -q`
Expected: FAIL because implementations do not exist yet

**Step 2: Implement the minimal extractor logic**

Implementation intent:
- compute features from the diff or extraction payload only
- keep evidence and hallucination checks explicit

**Step 3: Re-run the extractor tests**

Run: `pytest tests/extractors/test_minimal_diff.py tests/extractors/test_structured_extraction.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/extractors/minimal_diff.py src/modelfingerprint/extractors/structured_extraction.py tests/extractors/test_minimal_diff.py tests/extractors/test_structured_extraction.py tests/fixtures/extractors/minimal_diff tests/fixtures/extractors/structured_extraction
git commit -m "feat: add diff and structured extraction extractors"
```

### Task 5: Implement the `retrieval` extractor and seed the v1 prompt files

**Files:**
- Create: `src/modelfingerprint/extractors/retrieval.py`
- Create: `tests/extractors/test_retrieval.py`
- Create: `tests/fixtures/extractors/retrieval/`
- Create: `prompt-bank/candidates/p001.yaml`
- Create: `prompt-bank/candidates/p002.yaml`
- Continue until the initial v1 candidate set is seeded
- Create: `tests/prompt_bank/test_candidate_files.py`

**Step 1: Write failing retrieval and candidate-file tests**

Test intent:
- `retrieval` extracts hit count and confusion patterns
- every candidate file validates and references a known extractor
- released suites only reference existing candidate prompts

Run: `pytest tests/extractors/test_retrieval.py tests/prompt_bank/test_candidate_files.py -q`
Expected: FAIL because retrieval extractor and candidate prompt files do not exist yet

**Step 2: Implement the retrieval extractor**

Implementation intent:
- compute stable retrieval metrics from fixed-format outputs
- keep failure modes explicit rather than inferred from free text

**Step 3: Seed the candidate pool and released suites**

Implementation intent:
- start by checking in a v1 candidate set organized across the five families
- record `weight_hint`, `extractor`, and `output_contract` on every file
- keep `screening-v1` a strict subset of `default-v1`

**Step 4: Re-run the tests**

Run: `pytest tests/extractors/test_retrieval.py tests/prompt_bank/test_candidate_files.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/extractors/retrieval.py tests/extractors/test_retrieval.py tests/fixtures/extractors/retrieval prompt-bank/candidates prompt-bank/suites tests/prompt_bank/test_candidate_files.py
git commit -m "feat: add retrieval extractor and v1 prompt bank"
```
