import { spawn } from "node:child_process"
import { randomBytes } from "node:crypto"
import path from "node:path"

type BridgeCommand =
  | "list-fingerprints"
  | "create-run"
  | "get-run"
  | "get-result"
  | "cancel-run"

type BridgeErrorPayload = {
  error?: {
    code?: string
    message?: string
    status?: number
  }
}

export class PythonBridgeError extends Error {
  code: string
  status: number

  constructor(code: string, message: string, status: number) {
    super(message)
    this.code = code
    this.status = status
  }
}

type CreateRunRequest = {
  api_key: string
  base_url: string
  model_name: string
  fingerprint_model_id: string
}

function resolveRepoRoot() {
  return path.resolve(process.cwd(), "..", "..")
}

function bridgeCommand(command: BridgeCommand, args: string[] = []) {
  return [
    "run",
    "python",
    "-m",
    "modelfingerprint.webapi.bridge_cli",
    "--root",
    resolveRepoRoot(),
    command,
    ...args,
  ]
}

async function runBridge<T>(
  command: BridgeCommand,
  options: {
    args?: string[]
    env?: NodeJS.ProcessEnv
    input?: unknown
  } = {},
): Promise<T> {
  const cwd = resolveRepoRoot()

  return new Promise<T>((resolve, reject) => {
    const child = spawn("uv", bridgeCommand(command, options.args), {
      cwd,
      env: {
        ...process.env,
        ...options.env,
      },
      stdio: ["pipe", "pipe", "pipe"],
    })

    let stdout = ""
    let stderr = ""

    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString()
    })
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString()
    })
    child.on("error", (error) => {
      reject(new PythonBridgeError("TRANSPORT_ERROR", error.message, 500))
    })
    child.on("close", (code) => {
      const trimmed = stdout.trim()

      if (code === 0) {
        if (trimmed === "") {
          resolve(undefined as T)
          return
        }
        resolve(JSON.parse(trimmed) as T)
        return
      }

      if (trimmed !== "") {
        const payload = JSON.parse(trimmed) as BridgeErrorPayload
        reject(
          new PythonBridgeError(
            payload.error?.code ?? "TRANSPORT_ERROR",
            payload.error?.message ?? (stderr.trim() || "python bridge failed"),
            payload.error?.status ?? 500,
          ),
        )
        return
      }

      reject(
        new PythonBridgeError(
          "TRANSPORT_ERROR",
          stderr.trim() || "python bridge failed",
          500,
        ),
      )
    })

    if (options.input === undefined) {
      child.stdin.end()
      return
    }

    child.stdin.end(JSON.stringify(options.input))
  })
}

function spawnRunWorker(runId: string, apiKey: string) {
  const cwd = resolveRepoRoot()
  const worker = spawn(
    "uv",
    [
      "run",
      "python",
      "-m",
      "modelfingerprint.webapi.bridge_cli",
      "--root",
      cwd,
      "run-worker",
      "--run-id",
      runId,
    ],
    {
      cwd,
      env: {
        ...process.env,
        MODELFINGERPRINT_WEB_API_KEY: apiKey,
      },
      detached: true,
      stdio: "ignore",
    },
  )
  worker.unref()
}

export async function listFingerprints() {
  return runBridge<{ items: Array<Record<string, unknown>> }>("list-fingerprints")
}

export async function createRun(input: CreateRunRequest) {
  const runId = `run_${Date.now()}_${randomBytes(4).toString("hex")}`
  const payload = await runBridge<{
    run_id: string
    run_status: string
    result_state: string | null
    cancel_requested: boolean
  }>("create-run", {
    input: {
      run_id: runId,
      base_url: input.base_url,
      model_name: input.model_name,
      fingerprint_model_id: input.fingerprint_model_id,
    },
  })

  spawnRunWorker(runId, input.api_key)
  return payload
}

export async function getRun(runId: string) {
  return runBridge<Record<string, unknown>>("get-run", {
    args: ["--run-id", runId],
  })
}

export async function getRunResult(runId: string) {
  return runBridge<Record<string, unknown>>("get-result", {
    args: ["--run-id", runId],
  })
}

export async function cancelRun(runId: string) {
  return runBridge<{
    run_id: string
    run_status: string
    result_state: string | null
    cancel_requested: boolean
  }>("cancel-run", {
    args: ["--run-id", runId],
  })
}

export function isPythonBridgeError(
  error: unknown,
): error is PythonBridgeError {
  return error instanceof PythonBridgeError
}
