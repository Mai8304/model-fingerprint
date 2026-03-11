export const apiPaths = {
  fingerprints: "/api/v1/fingerprints",
  runs: "/api/v1/runs",
  run: (runId: string) => `/api/v1/runs/${runId}`,
  result: (runId: string) => `/api/v1/runs/${runId}/result`,
  cancel: (runId: string) => `/api/v1/runs/${runId}/cancel`,
} as const

export const runStatusValues = [
  "validating",
  "running",
  "completed",
  "configuration_error",
  "stopped",
] as const

export type RunStatus = (typeof runStatusValues)[number]

export const resultStateValues = [
  "formal_result",
  "provisional",
  "insufficient_evidence",
  "incompatible_protocol",
  "configuration_error",
  "stopped",
] as const

export type ResultState = (typeof resultStateValues)[number]

export const promptStatusValues = [
  "pending",
  "running",
  "completed",
  "failed",
  "stopped",
] as const

export type PromptStatus = (typeof promptStatusValues)[number]

export const runStageValues = [
  "config_validation",
  "endpoint_resolution",
  "capability_probe",
  "prompt_execution",
  "comparison",
] as const

export type RunStage = (typeof runStageValues)[number]

export const runStageStatusValues = [
  "pending",
  "running",
  "completed",
  "failed",
] as const

export type RunStageStatus = (typeof runStageStatusValues)[number]

export const errorCodeValues = [
  "INVALID_REQUEST",
  "UNKNOWN_FINGERPRINT_MODEL",
  "AMBIGUOUS_ENDPOINT_PROFILE",
  "AUTH_FAILED",
  "ENDPOINT_UNREACHABLE",
  "MODEL_NOT_FOUND",
  "RATE_LIMITED",
  "PROVIDER_SERVER_ERROR",
  "UNSUPPORTED_ENDPOINT_PROTOCOL",
  "RESPONSE_TIMEOUT",
  "TRANSPORT_ERROR",
  "UNPARSEABLE_RESPONSE",
  "CANONICALIZATION_ERROR",
  "UNSUPPORTED_CAPABILITY",
  "TRUNCATED_RESPONSE",
  "INSUFFICIENT_EVIDENCE",
  "INCOMPATIBLE_PROTOCOL",
  "RUN_STOPPED",
  "RUN_NOT_FOUND",
  "RUN_NOT_COMPLETED",
] as const

export type ErrorCode = (typeof errorCodeValues)[number]
