import { presentFailureMessage } from "@/lib/failure-presentation"
import type { LocaleKey } from "@/lib/i18n/messages"
import type { RunSnapshot } from "@/lib/run-types"

export function deriveRemoteFieldErrors(
  run: RunSnapshot,
  locale: LocaleKey = "en",
): Partial<Record<"apiKey" | "baseUrl" | "modelName" | "fingerprintModel", string>> {
  if (run.status !== "configuration_error" && run.resultState !== "configuration_error") {
    return {}
  }

  if (run.failureReason === undefined) {
    return {}
  }

  const field = run.failureField ?? fieldForErrorCode(run.failureCode)
  if (field === undefined || field === null) {
    return {}
  }

  return {
    [field]: presentFailureMessage({
      code: run.failureCode,
      message: run.failureReason,
      locale,
      fallback: run.failureReason,
    }),
  }
}

function fieldForErrorCode(code: RunSnapshot["failureCode"]) {
  switch (code) {
    case "AUTH_FAILED":
      return "apiKey"
    case "MODEL_NOT_FOUND":
      return "modelName"
    case "UNKNOWN_FINGERPRINT_MODEL":
      return "fingerprintModel"
    case "AMBIGUOUS_ENDPOINT_PROFILE":
    case "ENDPOINT_UNREACHABLE":
    case "UNSUPPORTED_ENDPOINT_PROTOCOL":
      return "baseUrl"
    default:
      return undefined
  }
}
