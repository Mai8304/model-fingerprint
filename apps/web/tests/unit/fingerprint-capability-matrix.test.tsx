import { render, screen, within } from "@testing-library/react"

import { FingerprintCapabilityMatrix } from "@/components/workbench/fingerprint-capability-matrix"
import { Providers } from "@/components/providers"
import type { FingerprintRegistryItem } from "@/lib/run-types"

const items: FingerprintRegistryItem[] = [
  {
    id: "nano-banana",
    label: "Nano Banana",
    suite_id: "fingerprint-suite-v3",
    available: true,
    image_generation: {
      status: "supported",
      confidence: 1,
    },
    vision_understanding: {
      status: "supported",
      confidence: 1,
    },
  },
  {
    id: "gemini-3-pro-preview",
    label: "Gemini 3 Pro Preview",
    suite_id: "fingerprint-suite-v3",
    available: true,
    image_generation: {
      status: "unsupported",
      confidence: 1,
    },
    vision_understanding: {
      status: "accepted_but_ignored",
      confidence: 2 / 3,
    },
  },
]

test("renders a model table with image and vision capability summaries", () => {
  render(
    <Providers initialLocale="en">
      <FingerprintCapabilityMatrix items={items} />
    </Providers>,
  )

  expect(screen.getByText("Fingerprint Capability Matrix")).toBeInTheDocument()
  expect(screen.getByText("Model")).toBeInTheDocument()
  expect(screen.getByText("Image")).toBeInTheDocument()
  expect(screen.getByText("Vision")).toBeInTheDocument()
  expect(screen.getByText("Nano Banana")).toBeInTheDocument()
  expect(screen.getByText("Gemini 3 Pro Preview")).toBeInTheDocument()
  expect(screen.getAllByText("Supported").length).toBeGreaterThan(1)
  expect(screen.getByText("Unsupported")).toBeInTheDocument()
  expect(screen.getByText("Request accepted, but capability did not take effect")).toBeInTheDocument()
  expect(screen.getByText("67%")).toBeInTheDocument()

  const panel = screen.getByRole("heading", { level: 3, name: "Fingerprint Capability Matrix" }).closest("section")
  const cells = within(panel as HTMLElement).getAllByRole("cell")
  expect(cells.length).toBeGreaterThan(0)
  for (const cell of cells) {
    expect(cell).toHaveClass("align-middle")
    expect(cell).not.toHaveClass("align-top")
  }
})

test("localizes the matrix headers and status labels", () => {
  render(
    <Providers initialLocale="zh-CN">
      <FingerprintCapabilityMatrix items={items} />
    </Providers>,
  )

  expect(screen.getByText("指纹模型能力矩阵")).toBeInTheDocument()
  expect(screen.getByText("模型")).toBeInTheDocument()
  expect(screen.getByText("文生图")).toBeInTheDocument()
  expect(screen.getByText("看图理解")).toBeInTheDocument()
  expect(screen.getAllByText("支持").length).toBeGreaterThan(1)
  expect(screen.getByText("不支持")).toBeInTheDocument()
  expect(screen.getByText("请求已接受，但能力未生效")).toBeInTheDocument()
})
