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

  expect(await screen.findByText("API Key is required.")).toBeInTheDocument()
  expect(await screen.findByText("Base URL must be a valid URL.")).toBeInTheDocument()
  expect(await screen.findByText("Model name is required.")).toBeInTheDocument()
  expect(await screen.findByText("Choose a fingerprint model.")).toBeInTheDocument()
  expect(onSubmit).not.toHaveBeenCalled()
})

test("renders remote field errors when provided", () => {
  const onSubmit = vi.fn()

  render(
    <Providers initialLocale="en">
      <CheckConfigForm
        disabled={false}
        onSubmit={onSubmit}
        remoteErrors={{
          apiKey: "provider rejected the supplied API key",
          modelName: "provider could not find the requested model",
        }}
      />
    </Providers>,
  )

  expect(screen.getByText("provider rejected the supplied API key")).toBeInTheDocument()
  expect(screen.getByText("provider could not find the requested model")).toBeInTheDocument()
})
