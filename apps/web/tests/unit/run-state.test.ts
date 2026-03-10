import { deriveWorkbenchState } from "@/lib/run-state"

test("maps 4 completed prompts to provisional observation", () => {
  const state = deriveWorkbenchState({
    status: "completed",
    completedPrompts: 4,
    totalPrompts: 5,
    incompatibleProtocol: false,
    stoppedByUser: false,
    selectedFingerprint: "claude-3.7-sonnet",
    topCandidate: "gpt-4.1-mini",
  })

  expect(state.kind).toBe("provisional")
})

test("incompatible protocol overrides provisional observation", () => {
  const state = deriveWorkbenchState({
    status: "completed",
    completedPrompts: 4,
    totalPrompts: 5,
    incompatibleProtocol: true,
    stoppedByUser: false,
    selectedFingerprint: "claude-3.7-sonnet",
    topCandidate: "gpt-4.1-mini",
  })

  expect(state.kind).toBe("incompatible_protocol")
})
