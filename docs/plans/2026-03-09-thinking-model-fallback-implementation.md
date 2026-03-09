# Thinking Model Fallback Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add configurable thinking-model fallback handling for OpenAI-compatible endpoints and regenerate the GLM-5 fingerprint profile using the new flow.

**Architecture:** Extend endpoint profiles with a thinking retry ladder that can override request body fields per attempt. Teach `LiveRunner` to retry on truncated/no-answer completions using this ladder while preserving existing HTTP retry behavior. Keep prompt scoring unchanged and regenerate the GLM-5 v2 runs/profile through the normal repository path.

**Tech Stack:** Python, Pydantic contracts, Typer CLI, pytest

---

### Task 1: Add failing contract and transport tests

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/contracts/test_contract_models.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_live_runner.py`

**Step 1: Write the failing test**

- Add contract coverage for endpoint profiles with a `thinking_policy`.
- Add live-runner coverage for:
  - retrying after a truncated completion with no answer
  - applying request overrides on later attempts
  - stopping after a successful answer-bearing retry

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/contracts/test_contract_models.py tests/transports/test_live_runner.py -q`

**Step 3: Write minimal implementation**

- Extend endpoint contracts.
- Update the OpenAI chat dialect to apply per-attempt request overrides.
- Update `LiveRunner` to execute the retry ladder.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/contracts/test_contract_models.py tests/transports/test_live_runner.py -q`

### Task 2: Wire endpoint profile validation and OpenRouter GLM-5 policy

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/contracts/endpoint.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/dialects/openai_chat.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/endpoint-profiles/openrouter-glm-5.yaml`

**Step 1: Add policy fields**

- Introduce endpoint-level request body overrides.
- Introduce a thinking retry ladder with bounded attempts.

**Step 2: Preserve current behavior by default**

- Endpoints without a thinking policy must behave exactly as before.

**Step 3: Configure GLM-5**

- First attempt uses current reasoning-enabled behavior.
- Later attempts raise output budget and then disable visible reasoning for answer-first fallback.

### Task 3: Verify the repository and regenerate artifacts

**Files:**
- Regenerate: `/Users/zhuangwei/Downloads/coding/modelfingerprint/runs/2026-03-09/*.fingerprint-suite-v2.json`
- Regenerate: `/Users/zhuangwei/Downloads/coding/modelfingerprint/profiles/fingerprint-suite-v2/glm-5.json`

**Step 1: Run focused verification**

Run:
- `uv run pytest tests/contracts/test_contract_models.py tests/transports/test_live_runner.py tests/extractors/test_v2_probe_extractors.py tests/run/test_feature_pipeline.py -q`
- `uv run ruff check src tests`
- `uv run mypy src`

**Step 2: Regenerate GLM-5 runs/profile**

- Delete the current GLM-5 v2 runs/profile artifacts.
- Re-run the suite three times using the normal CLI path and the OpenRouter endpoint profile.
- Rebuild the profile from those runs.

**Step 3: Inspect outputs**

- Confirm all prompts are completed and scoreable.
- Confirm no run contains truncated prompts.
- Confirm the new profile uses exactly three regenerated runs.
