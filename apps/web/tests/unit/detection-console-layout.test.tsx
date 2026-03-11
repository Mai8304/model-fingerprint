import { render, screen } from "@testing-library/react"

import { DetectionConsole } from "@/components/detection-console"
import { Providers } from "@/components/providers"

test("renders configuration and merged result panel", () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  expect(screen.getByText("Model Fingerprint")).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "Configuration" })).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "Result" })).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "How it works" })).toBeInTheDocument()
  expect(screen.getByText("Run Overview")).toBeInTheDocument()
  expect(screen.getByText("Stage Timeline")).toBeInTheDocument()
  expect(screen.getByText("Prompt Diagnostics")).toBeInTheDocument()
  expect(
    screen.getByText(
      "This panel will render the global run state, current probe, per-prompt status, and result conclusion.",
    ),
  ).toBeInTheDocument()
  expect(screen.getByText("Fingerprint training")).toBeInTheDocument()
  expect(screen.getByText("Fingerprint comparison")).toBeInTheDocument()
  expect(screen.getByText("Conclusion output")).toBeInTheDocument()
  expect(screen.queryByRole("region", { name: "Workbench" })).not.toBeInTheDocument()
  expect(screen.getByTestId("how-it-works-flow")).toHaveClass("flex-col", "lg:flex-row")
  expect(screen.getByRole("button", { name: "Change language" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Change theme" })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Open GitHub repository" })).toHaveAttribute(
    "href",
    "https://github.com/Mai8304/model-fingerprint",
  )
})
