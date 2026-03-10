import { render, screen } from "@testing-library/react"

import { DetectionConsole } from "@/components/detection-console"
import { Providers } from "@/components/providers"

test("renders configuration and workbench panels", () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  expect(screen.getByText("Model Fingerprint")).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "Configuration" })).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "Workbench" })).toBeInTheDocument()
})
