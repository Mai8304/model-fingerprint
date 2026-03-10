import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { vi } from "vitest"

import { CheckConfigForm } from "@/components/check-config-form"
import { Providers } from "@/components/providers"

test("shows validation errors before submit", async () => {
  const onSubmit = vi.fn()
  const user = userEvent.setup()

  render(
    <Providers initialLocale="en">
      <CheckConfigForm disabled={false} onSubmit={onSubmit} />
    </Providers>,
  )

  await user.click(screen.getByRole("button", { name: /start check/i }))

  expect(await screen.findByText("API key is required.")).toBeInTheDocument()
  expect(await screen.findByText("Base URL must be a valid URL.")).toBeInTheDocument()
  expect(await screen.findByText("Model name is required.")).toBeInTheDocument()
  expect(await screen.findByText("Choose a fingerprint model.")).toBeInTheDocument()
  expect(onSubmit).not.toHaveBeenCalled()
})
