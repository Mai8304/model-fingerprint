# Model Fingerprint Diagnostics Workbench Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Upgrade the web console from a summary card into a diagnostics-first workbench with real stage progress, prompt-level execution details, structured verdict reporting, structured insufficient-evidence reporting, and field-level remote error feedback.

**Architecture:** Extend the Python web run contracts and run-store update path so intermediate execution state is persisted during a live run. Then replace the compressed frontend result-card model with a diagnostics workbench that consumes richer snapshots plus a final detailed report endpoint. Keep polling for now; the main change is better server-side state projection and a UI that renders it directly instead of collapsing it into one status sentence.

**Tech Stack:** Python, Pydantic, Next.js, React, TypeScript, Tailwind CSS, official `shadcn/ui`, Vitest, Playwright

---

### Task 1: Add failing backend contract tests for diagnostics snapshots

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_fingerprints_api_contract.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`

**Step 1: Write the failing test**

Add tests that expect snapshot/report payloads to include:

- run-level stage metadata
- prompt-level `first_byte_ms`, `bytes_received`, `finish_reason`, `parse_status`
- structured insufficient-evidence blocking reasons
- structured formal-result comparison metrics

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/webapi/test_run_orchestrator.py tests/webapi/test_fingerprints_api_contract.py -q`
Expected: FAIL because the current contracts do not expose those fields.

**Step 3: Write minimal implementation**

Extend the web contracts in:

- `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/webapi/contracts.py`

Add the smallest new fields needed for the failing tests to pass.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/webapi/test_run_orchestrator.py tests/webapi/test_fingerprints_api_contract.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/webapi/test_run_orchestrator.py tests/webapi/test_fingerprints_api_contract.py src/modelfingerprint/webapi/contracts.py
git commit -m "test: extend web diagnostics contract coverage"
```

### Task 2: Persist stage and prompt progress during live execution

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/webapi/run_store.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/webapi/run_orchestrator.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/webapi/run_projection.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/suite_runner.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`

**Step 1: Write the failing test**

Add a test that simulates an in-flight run and expects:

- stage changes to be saved before final completion
- prompt status to move `pending -> running -> completed/failed`
- progress counts to update before the final result is written

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/webapi/test_run_orchestrator.py -q`
Expected: FAIL because the current implementation only writes `running` once and final prompts at completion.

**Step 3: Write minimal implementation**

Introduce a progress callback/event sink from the runner path to the run store, then:

- save `stage=config_validation`, `stage=endpoint_resolution`, `stage=capability_probe`, `stage=prompt_execution`, `stage=comparison`
- mark each prompt `running` before execution
- save prompt metrics immediately after completion or failure

Keep the update path incremental and file-based.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/webapi/test_run_orchestrator.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/webapi/run_store.py src/modelfingerprint/webapi/run_orchestrator.py src/modelfingerprint/webapi/run_projection.py src/modelfingerprint/services/suite_runner.py src/modelfingerprint/transports/live_runner.py tests/webapi/test_run_orchestrator.py
git commit -m "feat: persist live diagnostics progress for web runs"
```

### Task 3: Add a final diagnostics report endpoint and result mapping

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/lib/api-contract.ts`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/lib/api-client.ts`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/lib/run-types.ts`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/app/api/v1/runs/[run_id]/result/route.ts`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/webapi/run_orchestrator.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/tests/unit/api-client.test.ts`

**Step 1: Write the failing test**

Add a frontend contract test that expects a structured diagnostics report object with:

- verdict metrics
- candidate list
- coverage metrics
- blocking reasons
- prompt evidence breakdown

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run api-client.test.ts`
Expected: FAIL because the frontend types and API client do not know about the richer report shape.

**Step 3: Write minimal implementation**

Expose the richer final result/report fields through the existing result route or a dedicated report route, and update frontend types to consume that payload directly.

**Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test -- --run api-client.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/lib/api-contract.ts apps/web/lib/api-client.ts apps/web/lib/run-types.ts apps/web/app/api/v1/runs/[run_id]/result/route.ts src/modelfingerprint/webapi/run_orchestrator.py apps/web/tests/unit/api-client.test.ts
git commit -m "feat: expose structured diagnostics reports to web clients"
```

### Task 4: Replace the summary result card with a diagnostics workbench shell

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/detection-console.tsx`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/lib/run-state.ts`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/workbench/run-overview.tsx`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/workbench/stage-timeline.tsx`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/workbench/prompt-diagnostics-table.tsx`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/workbench/conclusion-panel.tsx`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/tests/unit/detection-console-diagnostics.test.tsx`

**Step 1: Write the failing test**

Add a render test that expects the workbench to show:

- run overview labels
- stage timeline entries
- prompt diagnostics rows
- a conclusion area placeholder

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run detection-console-diagnostics.test.tsx`
Expected: FAIL because the current UI still renders a compressed `ResultCard`.

**Step 3: Write minimal implementation**

Replace the right-column summary card with the diagnostics workbench components. Keep the current left configuration panel intact.

Do not add cosmetic-only panels. Only render surfaces needed for approved diagnostics behavior.

**Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test -- --run detection-console-diagnostics.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/components/detection-console.tsx apps/web/lib/run-state.ts apps/web/components/workbench/run-overview.tsx apps/web/components/workbench/stage-timeline.tsx apps/web/components/workbench/prompt-diagnostics-table.tsx apps/web/components/workbench/conclusion-panel.tsx apps/web/tests/unit/detection-console-diagnostics.test.tsx
git commit -m "feat: add diagnostics workbench layout"
```

### Task 5: Add insufficient-evidence and formal-result report components

**Files:**
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/workbench/insufficient-evidence-report.tsx`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/workbench/formal-result-report.tsx`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/workbench/conclusion-panel.tsx`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/tests/unit/conclusion-panel.test.tsx`

**Step 1: Write the failing test**

Add render tests for:

- a formal result showing verdict, similarities, candidates, and protocol issues
- an insufficient-evidence report showing blocking reasons, coverage gaps, and recommendations

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run conclusion-panel.test.tsx`
Expected: FAIL because the current conclusion UI is not structured enough.

**Step 3: Write minimal implementation**

Render specialized report blocks keyed by final result state. Keep the verdict sentence short and make the evidence tables visible by default.

**Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test -- --run conclusion-panel.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/components/workbench/insufficient-evidence-report.tsx apps/web/components/workbench/formal-result-report.tsx apps/web/components/workbench/conclusion-panel.tsx apps/web/tests/unit/conclusion-panel.test.tsx
git commit -m "feat: add structured diagnostics reports for web results"
```

### Task 6: Map remote failures back to form fields and technical error panels

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/check-config-form.tsx`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/components/detection-console.tsx`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/lib/error-presentation.ts`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/tests/unit/check-config-form.test.tsx`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/tests/unit/error-presentation.test.ts`

**Step 1: Write the failing test**

Add tests for mapping:

- `AUTH_FAILED` -> `apiKey`
- `MODEL_NOT_FOUND` -> `modelName`
- `ENDPOINT_UNREACHABLE` -> `baseUrl`
- generic provider failures -> run-level alert plus technical detail

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run check-config-form.test.tsx error-presentation.test.ts`
Expected: FAIL because remote error mapping does not exist yet.

**Step 3: Write minimal implementation**

Add a small mapping utility and update the form so local Zod errors and remote provider errors can coexist without losing technical detail.

**Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test -- --run check-config-form.test.tsx error-presentation.test.ts`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/components/check-config-form.tsx apps/web/components/detection-console.tsx apps/web/lib/error-presentation.ts apps/web/tests/unit/check-config-form.test.tsx apps/web/tests/unit/error-presentation.test.ts
git commit -m "feat: surface remote configuration errors in diagnostics ui"
```

### Task 7: Verify end-to-end diagnostics behavior

**Files:**
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/apps/web/tests/e2e/diagnostics-workbench.spec.ts`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_fingerprint_registry_main.py`

**Step 1: Write the failing test**

Add end-to-end coverage for:

- a run that progresses through visible stages
- a completed run with a structured result
- an invalid API key run with field-level error feedback

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test:e2e -- diagnostics-workbench.spec.ts`
Expected: FAIL because the UI and contract changes are not fully wired yet.

**Step 3: Write minimal implementation**

Complete any remaining data wiring and UI behavior required for the end-to-end path to pass.

**Step 4: Run tests to verify they pass**

Run:

```bash
pnpm --dir apps/web test -- --run
uv run pytest tests/webapi -q
pnpm --dir apps/web test:e2e -- diagnostics-workbench.spec.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add apps/web/tests/e2e/diagnostics-workbench.spec.ts tests/webapi/test_fingerprint_registry_main.py
git commit -m "test: verify diagnostics workbench end to end"
```
