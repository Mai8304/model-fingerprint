import { render, screen, within } from "@testing-library/react"

import { DetectionConsole } from "@/components/detection-console"
import { Providers } from "@/components/providers"

test("renders the approved single-column result sections in order", () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  expect(screen.getByText("Model Fingerprint")).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "Configuration" })).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "Result" })).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "How it works" })).toBeInTheDocument()
  expect(screen.queryByText("Run Overview")).not.toBeInTheDocument()
  expect(screen.queryByText("Stage Timeline")).not.toBeInTheDocument()
  expect(screen.queryByText("Comparison Metrics")).not.toBeInTheDocument()

  const resultRegion = screen.getByRole("region", { name: "Result" })
  const sectionHeadings = within(resultRegion)
    .getAllByRole("heading", { level: 3 })
    .map((heading) => heading.textContent)

  expect(sectionHeadings).toEqual([
    "Formal Conclusion",
    "Capability Probe",
    "Prompt Probe",
    "Detailed Diagnostics",
    "Similar Models (Top 5)",
  ])
  expect(screen.queryByTestId("result-workbench-supporting")).not.toBeInTheDocument()
  expect(screen.getByTestId("result-workbench")).toHaveClass("grid", "gap-6")
  expect(screen.getByTestId("how-it-works-flow")).toHaveClass("flex-col", "lg:flex-row")
  expect(screen.getByRole("button", { name: "Change language" })).toBeInTheDocument()
  expect(screen.getByRole("button", { name: "Change theme" })).toBeInTheDocument()
  expect(screen.getByRole("link", { name: "Open GitHub repository" })).toHaveAttribute(
    "href",
    "https://github.com/Mai8304/model-fingerprint",
  )
})

test("keeps the result panel shrinkable while prompt probe stays horizontally scrollable", () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  const resultRegion = screen.getByRole("region", { name: "Result" })
  expect(resultRegion).toHaveClass("min-w-0")
  expect(screen.getByTestId("prompt-probe-table")).toHaveClass("w-full", "min-w-[720px]")
})

test("renders the reduced prompt probe columns", () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  const promptProbe = screen.getByRole("heading", { level: 3, name: "Prompt Probe" }).closest("section")
  const headers = within(promptProbe as HTMLElement)
    .getAllByRole("columnheader")
    .map((header) => header.textContent)

  expect(headers).toEqual([
    "Prompt",
    "Status",
    "Similarity",
    "Scoreable",
    "Error",
    "Summary",
  ])

  const cells = within(promptProbe as HTMLElement).getAllByRole("cell")
  expect(cells.length).toBeGreaterThan(0)
  for (const cell of cells) {
    expect(cell).toHaveClass("align-middle")
    expect(cell).not.toHaveClass("align-top")
  }
})
