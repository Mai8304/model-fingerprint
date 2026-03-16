import { getPromptDisplayInfo, getPromptTitle } from "@/lib/prompt-copy"

test("returns localized capability-based prompt labels", () => {
  expect(getPromptDisplayInfo("p021", "zh-CN")).toEqual({
    title: "分析模型证据判断能力",
    stepLabel: "第 1 题",
  })
  expect(getPromptDisplayInfo("p023", "en")).toEqual({
    title: "Cautious Answering",
    stepLabel: "Question 3",
  })
})

test("returns the title for running progress copy", () => {
  expect(getPromptTitle("p024", "zh-CN")).toBe("分析模型状态推演能力")
  expect(getPromptTitle("unknown", "en")).toBe("unknown")
})
