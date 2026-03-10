# Model Fingerprint Web MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a single-page `shadcn/ui` web console that starts a real model-fingerprint run, shows five-prompt progress, renders formal/provisional/error outcomes correctly, and supports English, Simplified Chinese, Japanese plus `light/dark/system` themes.

**Architecture:** Add a new `apps/web` Next.js App Router frontend alongside the existing Python backend. Keep browser logic thin: the frontend owns locale/theme/UI state and polls a backend `run_id`; the backend remains the source of prompt execution, progress, and result semantics. Use small local translation dictionaries and a deterministic run-state mapper so abnormal cases such as `incompatible_protocol`, `insufficient evidence`, and `3/5 provisional observation` cannot drift across components.

**Tech Stack:** Next.js, React, TypeScript, Tailwind CSS, official `shadcn/ui`, `lucide-react`, `next-themes`, Zod, React Hook Form, Vitest, React Testing Library, Playwright, pnpm

---

### Task 1: Scaffold the Web App and Test Harness

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/next.config.ts`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/components.json`
- Create: `apps/web/vitest.config.ts`
- Create: `apps/web/vitest.setup.ts`
- Create: `apps/web/playwright.config.ts`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/app/globals.css`
- Test: `apps/web/tests/unit/app-shell.smoke.test.tsx`

**Step 1: Write the failing smoke test**

```tsx
import { render, screen } from "@testing-library/react"
import HomePage from "@/app/page"

test("renders the model fingerprint title", () => {
  render(<HomePage />)
  expect(screen.getByText(/model fingerprint/i)).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run app-shell.smoke.test.tsx`
Expected: fail because the app scaffold and test harness do not exist yet.

**Step 3: Scaffold the app and baseline tooling**

Run:

```bash
pnpm create next-app apps/web --ts --eslint --tailwind --app --use-pnpm --import-alias "@/*"
pnpm --dir apps/web add next-themes zod react-hook-form @hookform/resolvers lucide-react
pnpm --dir apps/web add -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event playwright
```

**Step 4: Add minimal app shell implementation**

```tsx
export default function HomePage() {
  return <main>Model Fingerprint</main>
}
```

**Step 5: Run test to verify it passes**

Run: `pnpm --dir apps/web test -- --run app-shell.smoke.test.tsx`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: scaffold model fingerprint web app"
```

### Task 2: Install Official shadcn/ui, Theme, and Locale Infrastructure

**Files:**
- Modify: `apps/web/components.json`
- Create: `apps/web/components/providers.tsx`
- Create: `apps/web/components/locale-switcher.tsx`
- Create: `apps/web/components/theme-switcher.tsx`
- Create: `apps/web/lib/i18n/messages.ts`
- Create: `apps/web/lib/i18n/locale.ts`
- Create: `apps/web/lib/theme.ts`
- Test: `apps/web/tests/unit/locale-resolution.test.ts`
- Test: `apps/web/tests/unit/providers-render.test.tsx`

**Step 1: Write the failing locale-resolution test**

```ts
import { resolveInitialLocale } from "@/lib/i18n/locale"

test("falls back to english for unsupported locales", () => {
  expect(resolveInitialLocale("fr-FR")).toBe("en")
})
```

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run locale-resolution.test.ts`
Expected: fail because locale utilities do not exist yet.

**Step 3: Install official shadcn/ui primitives and implement providers**

Run:

```bash
pnpm dlx shadcn@latest init
pnpm dlx shadcn@latest add button card input select progress badge alert dropdown-menu collapsible table skeleton alert-dialog separator
```

Create:

```tsx
export function Providers({ children }: { children: React.ReactNode }) {
  return children
}
```

Implement:

- locale resolver:
  - `zh-CN` -> `zh-CN`
  - `ja` -> `ja`
  - everything else -> `en`
- theme support using `next-themes`
- message dictionaries for `en`, `zh-CN`, `ja`

**Step 4: Run tests to verify locale and providers pass**

Run: `pnpm --dir apps/web test -- --run locale-resolution.test.ts providers-render.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web
git commit -m "feat: add web locale and theme infrastructure"
```

### Task 3: Build the Responsive Detection Console Shell

**Files:**
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/layout.tsx`
- Modify: `apps/web/app/globals.css`
- Create: `apps/web/components/top-bar.tsx`
- Create: `apps/web/components/detection-console.tsx`
- Create: `apps/web/components/method-sheet.tsx`
- Test: `apps/web/tests/unit/detection-console-layout.test.tsx`

**Step 1: Write the failing layout test**

```tsx
import { render, screen } from "@testing-library/react"
import { DetectionConsole } from "@/components/detection-console"

test("renders configuration and workbench panels", () => {
  render(<DetectionConsole />)
  expect(screen.getByText(/configuration/i)).toBeInTheDocument()
  expect(screen.getByText(/workbench/i)).toBeInTheDocument()
})
```

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run detection-console-layout.test.tsx`
Expected: FAIL with missing component/module errors.

**Step 3: Implement the shell**

Create a page with:

- compact top bar
- left `Card` for configuration
- right `Card` stack for workbench
- responsive mobile stacking
- subtle research-lab visual tokens in `globals.css`

Minimal component sketch:

```tsx
export function DetectionConsole() {
  return (
    <div className="grid gap-4 lg:grid-cols-[380px_minmax(0,1fr)]">
      <section aria-label="Configuration" />
      <section aria-label="Workbench" />
    </div>
  )
}
```

**Step 4: Run test to verify it passes**

Run: `pnpm --dir apps/web test -- --run detection-console-layout.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web
git commit -m "feat: add detection console shell"
```

### Task 4: Implement the Configuration Form and Local Validation

**Files:**
- Create: `apps/web/components/check-config-form.tsx`
- Create: `apps/web/lib/check-config-schema.ts`
- Create: `apps/web/lib/fingerprint-options.ts`
- Test: `apps/web/tests/unit/check-config-schema.test.ts`
- Test: `apps/web/tests/unit/check-config-form.test.tsx`

**Step 1: Write the failing schema test**

```ts
import { checkConfigSchema } from "@/lib/check-config-schema"

test("requires api key, base url, model name, and fingerprint model", () => {
  const result = checkConfigSchema.safeParse({})
  expect(result.success).toBe(false)
})
```

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run check-config-schema.test.ts`
Expected: FAIL because the schema does not exist.

**Step 3: Implement the form with React Hook Form + Zod**

Requirements:

- fields:
  - `apiKey`
  - `baseUrl`
  - `modelName`
  - `fingerprintModel`
- localized labels and helper text
- secure-input treatment for API key
- security note card
- disabled state when a run is validating or active

Minimal schema:

```ts
export const checkConfigSchema = z.object({
  apiKey: z.string().min(1),
  baseUrl: z.string().url(),
  modelName: z.string().min(1),
  fingerprintModel: z.string().min(1),
})
```

**Step 4: Run tests to verify the schema and form pass**

Run: `pnpm --dir apps/web test -- --run check-config-schema.test.ts check-config-form.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add apps/web
git commit -m "feat: add detection configuration form"
```

### Task 5: Implement Workbench State Mapping and Error Semantics

**Files:**
- Create: `apps/web/lib/run-types.ts`
- Create: `apps/web/lib/run-state.ts`
- Create: `apps/web/components/workbench/global-status-card.tsx`
- Create: `apps/web/components/workbench/current-probe-card.tsx`
- Create: `apps/web/components/workbench/prompt-status-table.tsx`
- Create: `apps/web/components/workbench/result-card.tsx`
- Create: `apps/web/components/workbench/run-log-panel.tsx`
- Test: `apps/web/tests/unit/run-state.test.ts`
- Test: `apps/web/tests/unit/result-card.test.tsx`

**Step 1: Write the failing run-state decision test**

```ts
import { deriveWorkbenchState } from "@/lib/run-state"

test("maps 4 completed prompts to provisional observation", () => {
  const state = deriveWorkbenchState({
    status: "completed",
    completedPrompts: 4,
    incompatibleProtocol: false,
    stoppedByUser: false,
  })
  expect(state.kind).toBe("provisional")
})
```

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run run-state.test.ts`
Expected: FAIL because the mapper does not exist.

**Step 3: Implement deterministic state mapping**

Map in this exact priority:

1. `configuration_error`
2. `stopped`
3. `incompatible_protocol`
4. `insufficient_evidence` for completed prompts `< 3`
5. `provisional` for completed prompts `3` or `4`
6. `formal_result` for completed prompts `5`

Also map machine-readable prompt error codes to localized short labels.

**Step 4: Implement result and workbench components against the mapper**

Render:

- empty state
- running state with completed/failed/pending counts
- provisional observation with cautious wording
- insufficient evidence with no candidate ranking
- incompatible protocol with no identity verdict
- formal conclusion only for `5/5`

**Step 5: Run tests to verify pass**

Run: `pnpm --dir apps/web test -- --run run-state.test.ts result-card.test.tsx`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: add workbench states and result semantics"
```

### Task 6: Wire Backend Run Creation, Polling, and Stop Flow

**Files:**
- Create: `apps/web/lib/api-client.ts`
- Create: `apps/web/hooks/use-run-session.ts`
- Modify: `apps/web/components/check-config-form.tsx`
- Modify: `apps/web/components/detection-console.tsx`
- Modify: `apps/web/components/workbench/*.tsx`
- Test: `apps/web/tests/unit/use-run-session.test.tsx`
- Test: `apps/web/tests/fixtures/run-validating.json`
- Test: `apps/web/tests/fixtures/run-running.json`
- Test: `apps/web/tests/fixtures/run-provisional.json`
- Test: `apps/web/tests/fixtures/run-insufficient.json`
- Test: `apps/web/tests/fixtures/run-formal.json`

**Step 1: Write the failing polling-hook test**

```tsx
import { renderHook } from "@testing-library/react"
import { useRunSession } from "@/hooks/use-run-session"

test("starts a run and polls status by run id", async () => {
  const { result } = renderHook(() => useRunSession())
  expect(result.current.startRun).toBeDefined()
})
```

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web test -- --run use-run-session.test.tsx`
Expected: FAIL because the hook and client do not exist.

**Step 3: Implement API client and polling contract**

Assume backend endpoints:

- `POST /api/runs`
- `GET /api/runs/:runId`
- `POST /api/runs/:runId/stop`

Client requirements:

- create run from form payload
- poll by `runId`
- stop polling on terminal state
- expose start/stop/retry actions
- preserve run state while language/theme changes

**Step 4: Render polling-driven UI**

Behavior:

- disable config fields while validating/running
- show `Stop Check` during active run
- unlock form on terminal states
- keep prompt table and logs visible after completion

**Step 5: Run tests to verify pass**

Run: `pnpm --dir apps/web test -- --run use-run-session.test.tsx`
Expected: PASS

**Step 6: Commit**

```bash
git add apps/web
git commit -m "feat: connect web console to run polling flow"
```

### Task 7: Add Visual Polish, Accessibility, and End-to-End Coverage

**Files:**
- Modify: `apps/web/app/globals.css`
- Modify: `apps/web/components/**/*.tsx`
- Create: `apps/web/tests/e2e/console-states.spec.ts`
- Create: `apps/web/tests/e2e/fixtures/*.json`
- Modify: `apps/web/playwright.config.ts`

**Step 1: Write the failing end-to-end state test**

```ts
import { test, expect } from "@playwright/test"

test("shows provisional observation for a 4/5 run", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByText(/provisional observation/i)).toBeVisible()
})
```

**Step 2: Run test to verify it fails**

Run: `pnpm --dir apps/web exec playwright test console-states.spec.ts`
Expected: FAIL until fixture-backed UI states exist and are wired.

**Step 3: Polish accessibility and visual semantics**

Add:

- keyboard-accessible language and theme menus
- accessible labels for all inputs and prompt-state badges
- consistent `lucide-react` icon usage
- `Skeleton` loading states
- reduced-motion-safe progress and transitions
- dark-mode token verification

**Step 4: Run full verification**

Run:

```bash
pnpm --dir apps/web test
pnpm --dir apps/web exec playwright test
pnpm --dir apps/web lint
pnpm --dir apps/web build
```

Expected:

- unit tests PASS
- Playwright scenarios PASS
- lint PASS
- production build PASS

**Step 5: Commit**

```bash
git add apps/web
git commit -m "feat: finish model fingerprint web mvp"
```

### Task 8: Document Operator and Backend Integration Assumptions

**Files:**
- Modify: `README.md`
- Create: `docs/plans/2026-03-10-model-fingerprint-web-mvp-contract-notes.md`
- Test: none

**Step 1: Write the documentation delta**

Document:

- where the web app lives
- required backend endpoints
- language fallback rules
- theme rules
- result-state semantics:
  - `5/5` formal
  - `3/5` or `4/5` provisional
  - `<3/5` insufficient evidence
  - protocol incompatibility overrides provisional

**Step 2: Review docs against the design and implementation plan**

Run: `rg -n "provisional|insufficient|incompatible protocol|language|theme" README.md docs/plans`
Expected: key semantics appear in the right docs.

**Step 3: Commit**

```bash
git add README.md docs/plans/2026-03-10-model-fingerprint-web-mvp-contract-notes.md
git commit -m "docs: add model fingerprint web integration notes"
```
