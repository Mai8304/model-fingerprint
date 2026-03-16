import { deriveRemoteFieldErrors } from "@/lib/error-presentation"

test("maps auth failures to the apiKey field", () => {
  expect(
    deriveRemoteFieldErrors({
      runId: "run_001",
      status: "configuration_error",
      resultState: "configuration_error",
      cancelRequested: false,
      completedPrompts: 0,
      failedPrompts: 0,
      totalPrompts: 5,
      currentPromptIndex: null,
      currentPromptId: null,
      currentPromptLabel: null,
      currentStageId: "capability_probe",
      currentStageMessage: "provider rejected the supplied API key",
      stages: [],
      prompts: [],
      selectedFingerprint: "GLM-5",
      failureCode: "AUTH_FAILED",
      failureReason: "provider rejected the supplied API key",
      failureField: "apiKey",
      result: null,
    }, "zh-CN"),
  ).toEqual({
    apiKey: "当前接口鉴权失败，请检查 API Key 是否正确。",
  })
})

test("maps endpoint failures to a localized baseUrl field error", () => {
  expect(
    deriveRemoteFieldErrors({
      runId: "run_002",
      status: "configuration_error",
      resultState: "configuration_error",
      cancelRequested: false,
      completedPrompts: 0,
      failedPrompts: 0,
      totalPrompts: 5,
      currentPromptIndex: null,
      currentPromptId: null,
      currentPromptLabel: null,
      currentStageId: "capability_probe",
      currentStageMessage: "unable to reach the configured endpoint",
      stages: [],
      prompts: [],
      selectedFingerprint: "GLM-5",
      failureCode: "ENDPOINT_UNREACHABLE",
      failureReason: "unable to reach the configured endpoint",
      failureField: null,
      result: null,
    }, "zh-CN"),
  ).toEqual({
    baseUrl: "当前接口无法连接，请检查 Base URL、域名解析和网络可达性。",
  })
})

test("hides raw network probe errors behind a user-facing baseUrl message", () => {
  expect(
    deriveRemoteFieldErrors({
      runId: "run_003",
      status: "configuration_error",
      resultState: "configuration_error",
      cancelRequested: false,
      completedPrompts: 0,
      failedPrompts: 0,
      totalPrompts: 5,
      currentPromptIndex: null,
      currentPromptId: null,
      currentPromptLabel: null,
      currentStageId: "capability_probe",
      currentStageMessage: "<urlopen error [Errno -2] Name or service not known>",
      stages: [],
      prompts: [],
      selectedFingerprint: "GLM-5",
      failureCode: "ENDPOINT_UNREACHABLE",
      failureReason:
        "<urlopen error [Errno -2] Name or service not known> | <urlopen error [Errno -2] Name or service not known>",
      failureField: "baseUrl",
      result: null,
    }, "zh-CN"),
  ).toEqual({
    baseUrl: "当前接口无法连接，请检查 Base URL、域名解析和网络可达性。",
  })
})
