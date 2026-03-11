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
    }),
  ).toEqual({
    apiKey: "provider rejected the supplied API key",
  })
})

test("maps endpoint failures to the baseUrl field", () => {
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
    }),
  ).toEqual({
    baseUrl: "unable to reach the configured endpoint",
  })
})
