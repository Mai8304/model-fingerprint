# V2 P2 Canonicalization and Thinking Feature Pipeline Implementation Plan

**Goal:** Add a canonicalization layer that tolerates semantically equivalent output shapes and a feature pipeline that captures answer, reasoning, surface, and transport evidence separately.

**Architecture:** Raw model outputs are not fed directly to extractors. Each prompt first canonicalizes the answer against a declared output contract, then extracts semantic features from canonical form and auxiliary surface features from the raw answer and reasoning channels.

**Tech Stack:** Python 3.12+, pytest, Pydantic v2

**Status:** Planned

**Acceptance Evidence:**
- `uv run pytest tests/canonicalizers tests/run/test_feature_pipeline.py -q`
- `uv run ruff check src tests`
- `uv run mypy src`

---

### Task 1: Add canonicalization contracts, registry, and error model

**Files:**
- Create: `src/modelfingerprint/canonicalizers/base.py`
- Create: `src/modelfingerprint/canonicalizers/registry.py`
- Create: `tests/canonicalizers/test_registry.py`

**Step 1: Write failing canonicalizer-registry tests**

Test intent:
- prompts resolve canonicalizers by declared output-contract id
- canonicalizers return typed canonical payloads plus normalization events
- ambiguous or invalid outputs raise typed canonicalization errors

Run: `uv run pytest tests/canonicalizers/test_registry.py -q`
Expected: FAIL because canonicalizers do not exist yet

**Step 2: Implement the registry and contracts**

Implementation intent:
- make canonicalization a distinct phase from feature extraction
- standardize normalization-event reporting
- keep canonicalizer registration explicit and testable

**Step 3: Re-run the tests**

Run: `uv run pytest tests/canonicalizers/test_registry.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/canonicalizers tests/canonicalizers/test_registry.py
git commit -m "feat: add canonicalization registry and error model"
```

### Task 2: Implement tolerant v2 canonicalizers for every released output contract

**Files:**
- Create: `src/modelfingerprint/canonicalizers/plain_text.py`
- Create: `src/modelfingerprint/canonicalizers/strict_json.py`
- Create: `src/modelfingerprint/canonicalizers/tagged_text.py`
- Create: `src/modelfingerprint/canonicalizers/structured_extraction.py`
- Create: `src/modelfingerprint/canonicalizers/retrieval.py`
- Create: `tests/canonicalizers/test_plain_text.py`
- Create: `tests/canonicalizers/test_strict_json.py`
- Create: `tests/canonicalizers/test_structured_extraction.py`
- Create: `tests/canonicalizers/test_retrieval.py`

**Step 1: Write failing canonicalizer tests**

Test intent:
- fenced JSON canonicalizes correctly
- `hallucinated: false` canonicalizes to an empty list
- `due date` canonicalizes to `due_date`
- list-shaped and map-shaped evidence inputs canonicalize to the same internal structure
- semantically wrong outputs remain wrong after canonicalization

Run: `uv run pytest tests/canonicalizers -q`
Expected: FAIL because the concrete v2 canonicalizers do not exist yet

**Step 2: Implement the canonicalizers**

Implementation intent:
- accept equivalent surface shapes
- preserve normalization events
- keep semantically wrong behavior visible

**Step 3: Re-run the canonicalizer tests**

Run: `uv run pytest tests/canonicalizers -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/canonicalizers tests/canonicalizers
git commit -m "feat: add tolerant canonicalizers for released output contracts"
```

### Task 3: Upgrade the feature pipeline to answer/reasoning/surface/transport namespaces

**Files:**
- Modify: `src/modelfingerprint/services/feature_pipeline.py`
- Modify: `src/modelfingerprint/extractors/base.py`
- Modify: `src/modelfingerprint/extractors/registry.py`
- Modify: `tests/run/test_feature_pipeline.py`

**Step 1: Write failing feature-pipeline tests**

Test intent:
- answer features are extracted from canonical output
- reasoning features are extracted from normalized reasoning text
- surface features are extracted from raw answer text
- transport features are extracted from normalized completion metadata
- canonicalization warnings are preserved in the prompt execution record

Run: `uv run pytest tests/run/test_feature_pipeline.py -q`
Expected: FAIL because the current pipeline only extracts one flat feature map from raw answer text

**Step 2: Implement the v2 feature pipeline**

Implementation intent:
- namespace features by channel
- keep extractors ignorant of provider-specific wire payloads
- avoid mixing reasoning text into answer extractors

**Step 3: Re-run the pipeline tests**

Run: `uv run pytest tests/run/test_feature_pipeline.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/feature_pipeline.py src/modelfingerprint/extractors/base.py src/modelfingerprint/extractors/registry.py tests/run/test_feature_pipeline.py
git commit -m "feat: add thinking-aware multi-channel feature pipeline"
```

### Task 4: Add generic reasoning and surface extractors

**Files:**
- Create: `src/modelfingerprint/extractors/reasoning_trace.py`
- Create: `src/modelfingerprint/extractors/surface_contract.py`
- Modify: `src/modelfingerprint/extractors/registry.py`
- Create: `tests/extractors/test_reasoning_trace.py`
- Create: `tests/extractors/test_surface_contract.py`

**Step 1: Write failing extractor tests**

Test intent:
- reasoning extractors capture step count, numbered-outline use, hedge density, and backtrack markers
- surface extractors detect fences, extra text, key-order habits, and contract retention

Run: `uv run pytest tests/extractors/test_reasoning_trace.py tests/extractors/test_surface_contract.py -q`
Expected: FAIL because reasoning and surface extractors do not exist yet

**Step 2: Implement the extractors**

Implementation intent:
- keep reasoning features generic and non-provider-specific
- keep surface compliance as auxiliary evidence, not the semantic source of truth

**Step 3: Re-run the tests**

Run: `uv run pytest tests/extractors/test_reasoning_trace.py tests/extractors/test_surface_contract.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/extractors/reasoning_trace.py src/modelfingerprint/extractors/surface_contract.py src/modelfingerprint/extractors/registry.py tests/extractors/test_reasoning_trace.py tests/extractors/test_surface_contract.py
git commit -m "feat: add reasoning and surface behavior extractors"
```

### Phase exit criteria

P2 is complete only when:

1. semantically equivalent shapes no longer crash extractors
2. reasoning text is captured separately from final answer text
3. every released prompt can produce semantic and surface evidence without ad hoc parsing logic
