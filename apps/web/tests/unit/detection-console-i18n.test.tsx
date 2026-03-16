import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

import { DetectionConsole } from "@/components/detection-console"
import { Providers } from "@/components/providers"

async function switchToChinese() {
  const user = userEvent.setup()

  await user.click(screen.getByRole("button", { name: "Change language" }))
  await user.click(screen.getByRole("menuitemradio", { name: "Simplified Chinese" }))

  return user
}

test("switches all visible shell copy to simplified chinese", async () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  await switchToChinese()

  expect(screen.getByText("配置")).toBeInTheDocument()
  expect(screen.getByText("检测结果")).toBeInTheDocument()
  expect(screen.getByText("如何工作")).toBeInTheDocument()
  expect(screen.getByText("指纹训练")).toBeInTheDocument()
  expect(screen.getByText("指纹比对")).toBeInTheDocument()
  expect(screen.getByText("输出结论")).toBeInTheDocument()
  expect(screen.queryByText("检测工作台")).not.toBeInTheDocument()
  expect(screen.getByText("正式结论")).toBeInTheDocument()
  expect(screen.getByText("能力探测")).toBeInTheDocument()
  expect(screen.getByText("Prompt 探测")).toBeInTheDocument()
  expect(screen.getByText("详细诊断信息")).toBeInTheDocument()
  expect(screen.getByText("验证模型身份，识别降智与替换")).toBeInTheDocument()
  expect(screen.queryByText("运行概览")).not.toBeInTheDocument()
  expect(screen.queryByText("阶段时间线")).not.toBeInTheDocument()
  expect(screen.queryByText("对比指标")).not.toBeInTheDocument()
  expect(screen.queryByText("诊断信息")).not.toBeInTheDocument()
  expect(screen.queryByText("提示诊断")).not.toBeInTheDocument()
  expect(screen.getByText("检测开始后，这里会先给出正式结论，再展开能力、Prompt 与详细诊断证据。")).toBeInTheDocument()
  expect(screen.getByRole("option", { name: "选择一个指纹" })).toBeInTheDocument()
  expect(document.title).toBe("模型指纹识别")
}, 10000)

test("uses the active locale for validation messages after switching language", async () => {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )

  const user = await switchToChinese()

  await user.click(screen.getByRole("button", { name: "开始检查" }))

  expect(await screen.findByText("API Key 为必填项。")).toBeInTheDocument()
  expect(await screen.findByText("Base URL 必须是有效的 URL。")).toBeInTheDocument()
  expect(await screen.findByText("模型名称为必填项。")).toBeInTheDocument()
  expect(await screen.findByText("请选择一个指纹模型。")).toBeInTheDocument()
})
