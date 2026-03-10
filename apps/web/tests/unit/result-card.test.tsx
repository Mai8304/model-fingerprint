import { render, screen } from "@testing-library/react"

import { ResultCard } from "@/components/workbench/result-card"
import { Providers } from "@/components/providers"
import { createTranslationHelpers } from "@/lib/i18n/locale"
import { deriveWorkbenchState } from "@/lib/run-state"

const copy = createTranslationHelpers("en")

test("renders provisional copy for 4/5 results", () => {
  const state = deriveWorkbenchState({
    status: "completed",
    completedPrompts: 4,
    totalPrompts: 5,
    incompatibleProtocol: false,
    stoppedByUser: false,
    selectedFingerprint: "claude-3.7-sonnet",
    topCandidate: "gpt-4.1-mini",
  }, copy)

  render(
    <Providers initialLocale="en">
      <ResultCard state={state} />
    </Providers>,
  )

  expect(screen.getByText(/Provisional observation/i)).toBeInTheDocument()
  expect(screen.getByText(/gpt-4.1-mini/i)).toBeInTheDocument()
})
