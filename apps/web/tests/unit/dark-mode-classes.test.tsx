import { render, screen } from "@testing-library/react"

import { DetectionConsole } from "@/components/detection-console"
import { Providers } from "@/components/providers"

test("applies dark theme classes to the primary mobile surfaces", () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  expect(screen.getByRole("region", { name: "Configuration" })).toHaveClass(
    "dark:border-slate-800",
    "dark:bg-slate-900/80",
  )
  expect(screen.getByRole("region", { name: "Result" })).toHaveClass(
    "dark:border-slate-800",
    "dark:bg-slate-900/80",
  )
  expect(screen.getByLabelText("API Key")).toHaveClass(
    "dark:border-slate-700",
    "dark:bg-slate-900",
    "dark:text-slate-100",
  )
  expect(screen.getByLabelText("Fingerprint Model")).toHaveClass(
    "dark:border-slate-700",
    "dark:bg-slate-900",
    "dark:text-slate-100",
  )
  expect(
    screen
      .getByText("Your API key is used only for this check and is not stored after the request completes.")
      .closest("div"),
  ).toHaveClass("dark:border-emerald-900/50", "dark:bg-emerald-950/30", "dark:text-emerald-200")
  expect(
    screen.getByRole("heading", { level: 3, name: "Formal Conclusion" }).closest("section"),
  ).toHaveClass("dark:border-slate-800", "dark:bg-slate-900/70")
  expect(screen.getByText("Fingerprint training").closest("div")).toHaveClass(
    "dark:border-slate-800",
    "dark:bg-slate-900/60",
  )
})
