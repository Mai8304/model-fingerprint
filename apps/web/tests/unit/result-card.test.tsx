import { render, screen } from "@testing-library/react"

import { ResultCard } from "@/components/workbench/result-card"
import { deriveWorkbenchState } from "@/lib/run-state"

test("renders provisional copy for 4/5 results", () => {
  const state = deriveWorkbenchState({
    status: "completed",
    completedPrompts: 4,
    totalPrompts: 5,
    incompatibleProtocol: false,
    stoppedByUser: false,
    selectedFingerprint: "claude-3.7-sonnet",
    topCandidate: "gpt-4.1-mini",
  })

  render(<ResultCard state={state} />)

  expect(screen.getByText(/Provisional observation/i)).toBeInTheDocument()
  expect(screen.getByText(/gpt-4.1-mini/i)).toBeInTheDocument()
})
