import { listFingerprints } from "@/lib/server/python-bridge"

export async function GET() {
  try {
    return Response.json(await listFingerprints())
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
