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
  expect(screen.getByText("Run Overview")).toBeInTheDocument()
  expect(screen.getByText("Stage Timeline")).toBeInTheDocument()
  expect(screen.getByText("Prompt Diagnostics")).toBeInTheDocument()
  expect(screen.getByText("该区域将展示全局运行状态、当前探测步骤、逐题状态和最终结论。")).toBeInTheDocument()
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
