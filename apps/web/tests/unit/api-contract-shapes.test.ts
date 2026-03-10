import {
  apiPaths,
  promptStatusValues,
  resultStateValues,
  runStatusValues,
} from "@/lib/api-contract"

test("freezes the web api path prefix and endpoint shapes", () => {
  expect(apiPaths.fingerprints).toBe("/api/v1/fingerprints")
  expect(apiPaths.runs).toBe("/api/v1/runs")
  expect(apiPaths.run("run_123")).toBe("/api/v1/runs/run_123")
  expect(apiPaths.result("run_123")).toBe("/api/v1/runs/run_123/result")
  expect(apiPaths.cancel("run_123")).toBe("/api/v1/runs/run_123/cancel")
})

test("freezes the approved lifecycle and result enums", () => {
  expect(runStatusValues).toEqual([
    "validating",
    "running",
    "completed",
    "configuration_error",
    "stopped",
  ])

  expect(resultStateValues).toEqual([
    "formal_result",
    "provisional",
    "insufficient_evidence",
    "incompatible_protocol",
    "configuration_error",
    "stopped",
  ])
})

test("freezes frontend prompt statuses used by the console", () => {
  expect(promptStatusValues).toEqual([
    "pending",
    "running",
    "completed",
    "failed",
    "stopped",
  ])
})
