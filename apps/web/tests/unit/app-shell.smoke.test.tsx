import { render, screen } from "@testing-library/react"

import { Providers } from "@/components/providers"
import HomePage from "@/app/page"

test("renders the model fingerprint title and tagline", () => {
  render(
    <Providers initialLocale="en">
      <HomePage />
    </Providers>,
  )

  expect(screen.getByText(/model fingerprint/i)).toBeInTheDocument()
  expect(
    screen.getByText("Verify model identity and detect downgrades or swaps"),
  ).toBeInTheDocument()
  expect(screen.getByRole("banner")).toHaveClass("bg-white/92", "border-slate-200")
})
