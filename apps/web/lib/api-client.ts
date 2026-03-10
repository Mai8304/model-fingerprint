import { apiPaths } from "@/lib/api-contract"
import type {
  FingerprintRegistryItem,
  RunBrief,
  RunResultResource,
  RunResource,
} from "@/lib/run-types"

type ErrorPayload = {
  error?: {
    code?: string
    message?: string
  }
}

export class ApiClientError extends Error {
  code: string
  status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

async function readJson<T>(response: Response): Promise<T | null> {
  const text = await response.text()
  if (text.trim() === "") {
    return null
  }

  return JSON.parse(text) as T
}

async function requestJson<T>(input: string, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init)
  const payload = await readJson<T | ErrorPayload>(response)

  if (!response.ok) {
    const error = payload as ErrorPayload | null
    throw new ApiClientError(
      error?.error?.code ?? "TRANSPORT_ERROR",
      error?.error?.message ?? "request failed",
      response.status,
    )
  }

  return payload as T
}

export async function listFingerprintModels(): Promise<FingerprintRegistryItem[]> {
  const payload = await requestJson<{ items: FingerprintRegistryItem[] }>(apiPaths.fingerprints)
  return payload.items.filter((item) => item.available)
}

export function createRun(input: {
  apiKey: string
  baseUrl: string
  modelName: string
  fingerprintModelId: string
}) {
  return requestJson<RunBrief>(apiPaths.runs, {
    method: "POST",
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify({
      api_key: input.apiKey,
      base_url: input.baseUrl,
      model_name: input.modelName,
      fingerprint_model_id: input.fingerprintModelId,
    }),
  })
}

export function getRun(runId: string) {
  return requestJson<RunResource>(apiPaths.run(runId))
}

export function getRunResult(runId: string) {
  return requestJson<RunResultResource>(apiPaths.result(runId))
}

export function cancelRun(runId: string) {
  return requestJson<RunBrief>(apiPaths.cancel(runId), {
    method: "POST",
  })
}
