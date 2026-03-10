import { render, screen } from "@testing-library/react"

import HomePage from "@/app/page"

test("renders the model fingerprint title", () => {
  render(<HomePage />)

  expect(screen.getByText(/model fingerprint/i)).toBeInTheDocument()
})
