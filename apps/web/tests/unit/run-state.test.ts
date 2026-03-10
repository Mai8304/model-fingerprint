import { createTranslationHelpers } from "@/lib/i18n/locale"
import { deriveWorkbenchState } from "@/lib/run-state"

const copy = createTranslationHelpers("en")

test("maps 4 completed prompts to provisional observation", () => {
  const state = deriveWorkbenchState({
    runId: "run_001",
    status: "completed",
    resultState: "provisional",
    cancelRequested: false,
    completedPrompts: 4,
    totalPrompts: 5,
    currentPromptId: null,
    currentPromptLabel: null,
    selectedFingerprint: "claude-3.7-sonnet",
    topCandidate: "gpt-4.1-mini",
  }, copy)

  expect(state.kind).toBe("provisional")
})

test("incompatible protocol overrides provisional observation", () => {
  const state = deriveWorkbenchState({
    runId: "run_002",
    status: "completed",
    resultState: "incompatible_protocol",
    cancelRequested: false,
    completedPrompts: 4,
    totalPrompts: 5,
    currentPromptId: null,
    currentPromptLabel: null,
    selectedFingerprint: "claude-3.7-sonnet",
    topCandidate: "gpt-4.1-mini",
  }, copy)

  expect(state.kind).toBe("incompatible_protocol")
})
