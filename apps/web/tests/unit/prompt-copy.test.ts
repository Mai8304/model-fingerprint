import { getPromptDisplayInfo, getPromptTitle } from "@/lib/prompt-copy"

test("returns localized v3.2 prompt labels and focus copy", () => {
  expect(getPromptDisplayInfo("p041", "zh-CN")).toEqual({
    title: "Prompt 1",
    stepLabel: null,
    focus: "复杂线索下的责任归因能力",
  })
  expect(getPromptDisplayInfo("p045", "en")).toEqual({
    title: "Prompt 5",
    stepLabel: null,
    focus: "Normalization thresholds for aliases and short names",
  })
})

test("keeps legacy prompt labels available for older suites", () => {
  expect(getPromptDisplayInfo("p021", "zh-CN")).toEqual({
    title: "分析模型证据判断能力",
    stepLabel: "第 1 题",
    focus: "证据判断能力",
  })
})

test("returns the title for running progress copy", () => {
  expect(getPromptTitle("p024", "zh-CN")).toBe("分析模型状态推演能力")
  expect(getPromptTitle("unknown", "en")).toBe("unknown")
})
