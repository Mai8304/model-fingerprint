import { z } from "zod"

import { createRun } from "@/lib/server/python-bridge"

const createRunSchema = z.object({
  api_key: z.string().trim().min(1),
  base_url: z.string().trim().url(),
  model_name: z.string().trim().min(1),
  fingerprint_model_id: z.string().trim().min(1),
})

export async function POST(request: Request) {
  let payload: unknown
  try {
    payload = await request.json()
  } catch {
    return Response.json(
      {
        error: {
          code: "INVALID_REQUEST",
          message: "request body must be valid JSON",
        },
      },
      { status: 400 },
    )
  }

  const parsed = createRunSchema.safeParse(payload)
  if (!parsed.success) {
    return Response.json(
      {
        error: {
          code: "INVALID_REQUEST",
          message: "request body is invalid",
        },
      },
      { status: 400 },
    )
  }

  try {
    const created = await createRun(parsed.data)
    return Response.json(created, { status: 201 })
  } catch (error) {
    return toErrorResponse(error)
  }
}

function toErrorResponse(error: unknown) {
  const payload = asErrorPayload(error)
  return Response.json({ error: payload.body }, { status: payload.status })
}

function asErrorPayload(error: unknown) {
  if (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error &&
    "status" in error
  ) {
    return {
      status: Number(error.status),
      body: {
        code: String(error.code),
        message: String(error.message),
      },
    }
  }

  return {
    status: 500,
    body: {
      code: "TRANSPORT_ERROR",
      message: "python bridge failed",
    },
  }
}
