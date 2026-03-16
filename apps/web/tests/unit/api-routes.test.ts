import { vi } from "vitest"

const bridgeMocks = vi.hoisted(() => ({
  listFingerprints: vi.fn(),
  createRun: vi.fn(),
  getRun: vi.fn(),
  getRunResult: vi.fn(),
  cancelRun: vi.fn(),
}))

vi.mock("@/lib/server/python-bridge", () => ({
  listFingerprints: bridgeMocks.listFingerprints,
  createRun: bridgeMocks.createRun,
  getRun: bridgeMocks.getRun,
  getRunResult: bridgeMocks.getRunResult,
  cancelRun: bridgeMocks.cancelRun,
}))

import { GET as getFingerprintsRoute } from "@/app/api/v1/fingerprints/route"
import { POST as createRunRoute } from "@/app/api/v1/runs/route"
import { POST as cancelRunRoute } from "@/app/api/v1/runs/[run_id]/cancel/route"
import { GET as getRunResultRoute } from "@/app/api/v1/runs/[run_id]/result/route"
import { GET as getRunRoute } from "@/app/api/v1/runs/[run_id]/route"

beforeEach(() => {
  vi.resetAllMocks()
})

test("GET /api/v1/fingerprints returns the V3 fingerprint registry", async () => {
  bridgeMocks.listFingerprints.mockResolvedValue({
    items: [
      {
        id: "glm-5",
        label: "GLM-5",
        suite_id: "fingerprint-suite-v3",
        available: true,
        image_generation: {
          status: "unsupported",
          confidence: 1,
        },
        vision_understanding: {
          status: "unsupported",
          confidence: 1,
        },
      },
    ],
  })

  const response = await getFingerprintsRoute()

  expect(response.status).toBe(200)
  await expect(response.json()).resolves.toEqual({
    items: [
      {
        id: "glm-5",
        label: "GLM-5",
        suite_id: "fingerprint-suite-v3",
        available: true,
        image_generation: {
          status: "unsupported",
          confidence: 1,
        },
        vision_understanding: {
          status: "unsupported",
          confidence: 1,
        },
      },
    ],
  })
})

test("POST /api/v1/runs returns a validating snapshot without api_key", async () => {
  bridgeMocks.createRun.mockResolvedValue({
    run_id: "run_123",
    run_status: "validating",
    result_state: null,
    cancel_requested: false,
  })

  const response = await createRunRoute(
    new Request("http://localhost/api/v1/runs", {
      method: "POST",
      body: JSON.stringify({
        api_key: "secret-key",
        base_url: "https://api.example.com/v1",
        model_name: "gpt-4o-mini",
        fingerprint_model_id: "glm-5",
      }),
      headers: {
        "content-type": "application/json",
      },
    }),
  )

  expect(bridgeMocks.createRun).toHaveBeenCalledWith({
    api_key: "secret-key",
    base_url: "https://api.example.com/v1",
    model_name: "gpt-4o-mini",
    fingerprint_model_id: "glm-5",
  })
  expect(response.status).toBe(201)
  await expect(response.json()).resolves.toEqual({
    run_id: "run_123",
    run_status: "validating",
    result_state: null,
    cancel_requested: false,
  })
})

test("GET /api/v1/runs/[run_id] returns the polling snapshot", async () => {
  bridgeMocks.getRun.mockResolvedValue({
    run_id: "run_123",
    run_status: "running",
    result_state: null,
    cancel_requested: false,
    created_at: "2026-03-10T14:30:00+08:00",
    updated_at: "2026-03-10T14:33:12+08:00",
    input: {
      base_url: "https://api.example.com/v1",
      model_name: "gpt-4o-mini",
      fingerprint_model_id: "glm-5",
    },
    progress: {
      completed_prompts: 2,
      failed_prompts: 0,
      total_prompts: 5,
      current_prompt_id: "p023",
      eta_seconds: 360,
    },
    prompts: [],
    failure: null,
  })

  const response = await getRunRoute(
    new Request("http://localhost/api/v1/runs/run_123"),
    { params: Promise.resolve({ run_id: "run_123" }) },
  )

  expect(response.status).toBe(200)
  await expect(response.json()).resolves.toMatchObject({
    run_id: "run_123",
    run_status: "running",
    progress: {
      total_prompts: 5,
      current_prompt_id: "p023",
    },
  })
})

test("GET /api/v1/runs/[run_id]/result returns 409 when the run is not completed", async () => {
  bridgeMocks.getRunResult.mockRejectedValue({
    code: "RUN_NOT_COMPLETED",
    message: "run is still in progress",
    status: 409,
  })

  const response = await getRunResultRoute(
    new Request("http://localhost/api/v1/runs/run_123/result"),
    { params: Promise.resolve({ run_id: "run_123" }) },
  )

  expect(response.status).toBe(409)
  await expect(response.json()).resolves.toEqual({
    error: {
      code: "RUN_NOT_COMPLETED",
      message: "run is still in progress",
    },
  })
})

test("POST /api/v1/runs/[run_id]/cancel returns 202 and the cancel flag", async () => {
  bridgeMocks.cancelRun.mockResolvedValue({
    run_id: "run_123",
    run_status: "running",
    result_state: null,
    cancel_requested: true,
  })

  const response = await cancelRunRoute(
    new Request("http://localhost/api/v1/runs/run_123/cancel", { method: "POST" }),
    { params: Promise.resolve({ run_id: "run_123" }) },
  )

  expect(response.status).toBe(202)
  await expect(response.json()).resolves.toEqual({
    run_id: "run_123",
    run_status: "running",
    result_state: null,
    cancel_requested: true,
  })
})
