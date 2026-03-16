import { render, screen, within } from "@testing-library/react"

import { CapabilityProbePanel } from "@/components/workbench/capability-probe-panel"
import { Providers } from "@/components/providers"
import type { RunSnapshot } from "@/lib/run-types"

function buildRunSnapshot(): RunSnapshot {
  return {
    runId: "run_capability_probe",
    status: "running",
    resultState: null,
    cancelRequested: false,
    completedPrompts: 0,
    failedPrompts: 0,
    totalPrompts: 5,
    currentPromptIndex: null,
    currentPromptId: null,
    currentPromptLabel: null,
    currentStageId: "capability_probe",
    currentStageMessage:
      "capability probe completed: thinking=supported, tools=accepted_but_ignored, streaming=supported, image_generation=supported, vision_understanding=accepted_but_ignored",
    stages: [
      {
        id: "capability_probe",
        status: "completed",
        message:
          "capability probe completed: thinking=supported, tools=accepted_but_ignored, streaming=supported, image_generation=supported, vision_understanding=accepted_but_ignored",
        started_at: "2026-03-11T08:00:00Z",
        finished_at: "2026-03-11T08:00:02Z",
      },
    ],
    prompts: [],
    selectedFingerprint: "GLM-5",
    result: null,
  }
}

test("renders five fixed capability rows with english primary labels and localized notes", () => {
  render(
    <Providers initialLocale="en">
      <CapabilityProbePanel run={buildRunSnapshot()} />
    </Providers>,
  )

  expect(screen.getByText("Thinking")).toBeInTheDocument()
  expect(screen.getByText("Tools")).toBeInTheDocument()
  expect(screen.getAllByText("Streaming").length).toBeGreaterThan(0)
  expect(screen.getByText("Image")).toBeInTheDocument()
  expect(screen.getByText("Vision")).toBeInTheDocument()
  expect(screen.getByText("Chain of thought")).toBeInTheDocument()
  expect(screen.getByText("Tool calls")).toBeInTheDocument()
  expect(screen.getAllByText("Streaming").length).toBeGreaterThan(1)
  expect(screen.getByText("Image generation")).toBeInTheDocument()
  expect(screen.getByText("Visual understanding")).toBeInTheDocument()

  const panel = screen.getByRole("heading", { level: 3, name: "Capability Probe" }).closest("section")
  const cells = within(panel as HTMLElement).getAllByRole("cell")
  expect(cells.length).toBeGreaterThan(0)
  for (const cell of cells) {
    expect(cell).toHaveClass("align-middle")
    expect(cell).not.toHaveClass("align-top")
  }
})

test("localizes capability notes in simplified chinese", () => {
  render(
    <Providers initialLocale="zh-CN">
      <CapabilityProbePanel run={buildRunSnapshot()} />
    </Providers>,
  )

  expect(screen.getByText("Thinking")).toBeInTheDocument()
  expect(screen.getByText("Tools")).toBeInTheDocument()
  expect(screen.getByText("Streaming")).toBeInTheDocument()
  expect(screen.getByText("Image")).toBeInTheDocument()
  expect(screen.getByText("Vision")).toBeInTheDocument()
  expect(screen.getByText("思考链")).toBeInTheDocument()
  expect(screen.getByText("工具调用")).toBeInTheDocument()
  expect(screen.getByText("流式输出")).toBeInTheDocument()
  expect(screen.getByText("文生图")).toBeInTheDocument()
  expect(screen.getByText("看图理解")).toBeInTheDocument()
})
