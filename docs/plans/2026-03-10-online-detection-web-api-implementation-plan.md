# Online Detection Web API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a real `/api/v1` backend for the web console that starts one online detection run, reports five-prompt progress, exposes terminal results, and aligns strictly with `docs/apis/web_api_contract.md`.

**Architecture:** Keep the browser thin and polling-based. Add a small web-facing orchestration layer that wraps the existing Python engine semantics, persists run state outside the browser, and maps engine artifacts into the HTTP resource shapes defined in `docs/apis/web_api_contract.md`. Reuse existing run/comparison contracts and verdict logic instead of creating a second result model.

**Tech Stack:** Next.js App Router route handlers, TypeScript, Python 3.12+, Typer/Pydantic engine contracts, JSON Schema, Vitest, pytest, Playwright

---

### Task 1: Freeze the Web API contract in tests and docs

**Files:**
- Modify: `docs/apis/web_api_contract.md`
- Test: `apps/web/tests/unit/api-contract-shapes.test.ts`

**Step 1: Write the failing contract-shape test**

Add a test that asserts the frontend-side expected enums and field names:

```ts
expect(runStatusValues).toEqual([
  "validating",
  "running",
  "completed",
  "configuration_error",
  "stopped",
])
```

**Step 2: Run test to verify it fails**

Run: `npm test -- api-contract-shapes`
Expected: FAIL because the client contract module does not exist yet.

**Step 3: Add the frontend contract constants/types**

Create a small client contract module that mirrors:

- endpoint paths
- `run_status`
- `result_state`
- prompt status values
- error code names

**Step 4: Run test to verify it passes**

Run: `npm test -- api-contract-shapes`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/apis/web_api_contract.md apps/web/tests/unit/api-contract-shapes.test.ts apps/web/lib/api-contract.ts
git commit -m "docs: freeze online detection web api contract"
```

### Task 2: Add a fingerprint registry projection for the web API

**Files:**
- Create: `src/modelfingerprint/webapi/fingerprints.py`
- Create: `src/modelfingerprint/webapi/contracts.py`
- Test: `tests/webapi/test_fingerprints_api_contract.py`
- Modify: `apps/web/lib/fingerprint-options.ts`

**Step 1: Write the failing backend test**

Add a test that loads the available profiles/fingerprint artifacts and asserts the API projection shape:

```python
assert item["id"] == "claude-3.7-sonnet"
assert "suite_id" in item
assert item["available"] is True
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/webapi/test_fingerprints_api_contract.py -q`
Expected: FAIL because the web API projection module does not exist yet.

**Step 3: Implement the registry projection**

Create a small service that returns web-facing `fingerprint_model` items from existing stored profiles or registry metadata. The web registry should read from `profiles/fingerprint-suite-v3`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/webapi/test_fingerprints_api_contract.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/webapi/fingerprints.py src/modelfingerprint/webapi/contracts.py tests/webapi/test_fingerprints_api_contract.py apps/web/lib/fingerprint-options.ts
git commit -m "feat: add web fingerprint registry projection"
```

### Task 3: Introduce a persistent run registry and state projection

**Files:**
- Create: `src/modelfingerprint/webapi/run_store.py`
- Create: `src/modelfingerprint/webapi/run_projection.py`
- Test: `tests/webapi/test_run_projection.py`
- Test: `tests/webapi/test_run_store.py`

**Step 1: Write the failing run-store and projection tests**

Cover:

- creating a run record
- updating progress
- marking terminal state
- projecting `RunArtifact` plus runtime state into the HTTP `run` resource

**Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/webapi/test_run_store.py tests/webapi/test_run_projection.py -q`
Expected: FAIL because these modules do not exist yet.

**Step 3: Implement minimal run persistence and projection**

Persist enough state to support:

- `run_id`
- lifecycle state
- cancel flag
- prompt progress
- terminal failure
- terminal result-state marker

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/webapi/test_run_store.py tests/webapi/test_run_projection.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/webapi/run_store.py src/modelfingerprint/webapi/run_projection.py tests/webapi/test_run_store.py tests/webapi/test_run_projection.py
git commit -m "feat: add web run store and snapshot projection"
```

### Task 4: Add orchestration that wraps capability probing, suite execution, and comparison

**Files:**
- Create: `src/modelfingerprint/webapi/run_orchestrator.py`
- Modify: `src/modelfingerprint/services/suite_runner.py`
- Test: `tests/webapi/test_run_orchestrator.py`
- Test: `tests/e2e/test_live_endpoint_profiles.py`

**Step 1: Write the failing orchestrator test**

Cover:

- create run -> enters `validating`
- successful probe -> enters `running`
- suite completion -> writes terminal result
- upstream auth failure -> lands in `configuration_error`
- protocol incompatibility -> lands in `completed + incompatible_protocol`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/webapi/test_run_orchestrator.py -q`
Expected: FAIL because orchestrator wiring does not exist yet.

**Step 3: Implement minimal orchestration**

Wrap existing engine/service calls:

- capability probe
- runtime policy resolution
- `fingerprint-suite-v3` execution
- comparison artifact build and verdict decision

Update run store between phases so polling can observe progress.

**Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/webapi/test_run_orchestrator.py tests/e2e/test_live_endpoint_profiles.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/webapi/run_orchestrator.py src/modelfingerprint/services/suite_runner.py tests/webapi/test_run_orchestrator.py tests/e2e/test_live_endpoint_profiles.py
git commit -m "feat: orchestrate web runs from existing engine services"
```

### Task 5: Add cooperative cancellation

**Files:**
- Modify: `src/modelfingerprint/webapi/run_store.py`
- Modify: `src/modelfingerprint/webapi/run_orchestrator.py`
- Test: `tests/webapi/test_run_cancellation.py`

**Step 1: Write the failing cancellation test**

Cover:

- cancel request sets `cancel_requested=true`
- active run eventually transitions to `stopped`
- cancel does not leak a false formal result

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/webapi/test_run_cancellation.py -q`
Expected: FAIL because cooperative cancellation is not wired yet.

**Step 3: Implement minimal cancellation handling**

Use a cancel flag checked between request read loops or prompt boundaries. Ensure the run settles into `stopped`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/webapi/test_run_cancellation.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/webapi/run_store.py src/modelfingerprint/webapi/run_orchestrator.py tests/webapi/test_run_cancellation.py
git commit -m "feat: add cooperative cancellation for web runs"
```

### Task 6: Expose `/api/v1` HTTP endpoints

**Files:**
- Create: `apps/web/app/api/v1/fingerprints/route.ts`
- Create: `apps/web/app/api/v1/runs/route.ts`
- Create: `apps/web/app/api/v1/runs/[run_id]/route.ts`
- Create: `apps/web/app/api/v1/runs/[run_id]/result/route.ts`
- Create: `apps/web/app/api/v1/runs/[run_id]/cancel/route.ts`
- Create: `apps/web/lib/server/python-bridge.ts`
- Test: `apps/web/tests/unit/api-routes.test.ts`

**Step 1: Write the failing route tests**

Cover:

- `GET /api/v1/fingerprints`
- `POST /api/v1/runs`
- `GET /api/v1/runs/{id}`
- `GET /api/v1/runs/{id}/result`
- `POST /api/v1/runs/{id}/cancel`

Assert:

- status codes
- field names
- missing `api_key` in responses
- `409 RUN_NOT_COMPLETED` behavior

**Step 2: Run test to verify it fails**

Run: `npm test -- api-routes`
Expected: FAIL because route handlers do not exist yet.

**Step 3: Implement thin route handlers**

The handlers should:

- validate request payloads
- delegate to backend orchestration
- serialize strictly to `docs/apis/web_api_contract.md`
- never embed frontend-localized prose

**Step 4: Run test to verify it passes**

Run: `npm test -- api-routes`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/app/api/v1 apps/web/lib/server/python-bridge.ts apps/web/tests/unit/api-routes.test.ts
git commit -m "feat: expose online detection web api routes"
```

### Task 7: Connect the web console to the real API

**Files:**
- Modify: `apps/web/components/check-config-form.tsx`
- Modify: `apps/web/components/detection-console.tsx`
- Modify: `apps/web/lib/run-types.ts`
- Modify: `apps/web/lib/run-state.ts`
- Create: `apps/web/lib/api-client.ts`
- Create: `apps/web/lib/prompt-copy.ts`
- Test: `apps/web/tests/unit/detection-console-live.test.tsx`

**Step 1: Write the failing integration-style UI test**

Cover:

- submit form -> `POST /api/v1/runs`
- polling updates progress
- completed run shows correct terminal state
- provisional and insufficient-evidence rendering follows the contract

**Step 2: Run test to verify it fails**

Run: `npm test -- detection-console-live`
Expected: FAIL because the console is still static.

**Step 3: Implement minimal live wiring**

Add:

- API client helpers
- form submit -> create run
- polling loop
- stop button -> cancel endpoint
- prompt id to localized label mapping

**Step 4: Run test to verify it passes**

Run: `npm test -- detection-console-live`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/components/check-config-form.tsx apps/web/components/detection-console.tsx apps/web/lib/run-types.ts apps/web/lib/run-state.ts apps/web/lib/api-client.ts apps/web/lib/prompt-copy.ts apps/web/tests/unit/detection-console-live.test.tsx
git commit -m "feat: connect detection console to live api"
```

### Task 8: End-to-end verification and contract lock

**Files:**
- Modify: `docs/apis/web_api_contract.md`
- Create: `apps/web/output/playwright/`
- Test: `tests/webapi/`
- Test: `apps/web/tests/unit/`

**Step 1: Run backend verification**

Run:

```bash
uv run pytest tests/webapi tests/e2e/test_live_endpoint_profiles.py -q
```

Expected: PASS

**Step 2: Run web verification**

Run:

```bash
npm test
npm run build
```

Expected: PASS

**Step 3: Run browser verification**

Use Playwright against `http://localhost:3000` and verify:

- fingerprint list loads
- run starts
- polling updates progress
- result page changes across formal, provisional, and insufficient-evidence fixtures
- language switching still localizes all UI-owned strings

**Step 4: Update contract doc if the implementation surfaced missing fields**

Only add fields if they are proven necessary. Do not widen the contract speculatively.

**Step 5: Commit**

```bash
git add docs/apis/web_api_contract.md apps/web/output/playwright
git commit -m "test: verify live web api contract end to end"
```
