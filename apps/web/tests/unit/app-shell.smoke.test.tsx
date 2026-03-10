import { render, screen } from "@testing-library/react"

import { Providers } from "@/components/providers"
import HomePage from "@/app/page"

test("renders the model fingerprint title", () => {
  render(
    <Providers initialLocale="en">
      <HomePage />
    </Providers>,
  )

  expect(screen.getByText(/model fingerprint/i)).toBeInTheDocument()
})
