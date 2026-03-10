import type { ErrorCode, PromptStatus, ResultState, RunStatus } from "@/lib/api-contract"

export type FingerprintOption = {
  value: string
  label: string
}

export type FingerprintRegistryItem = {
  id: string
  label: string
  suite_id: string
  available: boolean
}

export type RunBrief = {
  run_id: string
  run_status: RunStatus
  result_state: ResultState | null
  cancel_requested: boolean
}

export type RunPromptResource = {
  prompt_id: string
  status: PromptStatus
  elapsed_seconds: number | null
  summary_code: string | null
  error_code: ErrorCode | null
  error_detail: string | null
  http_status: number | null
}

export type RunResource = {
  run_id: string
  run_status: RunStatus
  result_state: ResultState | null
  cancel_requested: boolean
  created_at: string
  updated_at: string
  input: {
    base_url: string
    model_name: string
    fingerprint_model_id: string
  }
  progress: {
    completed_prompts: number
    failed_prompts: number
    total_prompts: number
    current_prompt_id: string | null
    eta_seconds: number | null
  }
  prompts: RunPromptResource[]
  failure: {
    code: ErrorCode
    message: string | null
    retryable?: boolean | null
    http_status?: number | null
  } | null
}

export type RunResultResource = {
  run_id: string
  result_state: ResultState
  selected_fingerprint: {
    id: string
    label: string
  }
  completed_prompts: number
  total_prompts: number
  verdict: string | null
  summary: {
    similarity_score: number | null
    confidence_low: number | null
    confidence_high: number | null
    top_candidate_model_id: string | null
    top_candidate_label: string | null
  } | null
  candidates: Array<{
    model_id: string
    label: string
    similarity: number
  }>
  diagnostics: {
    protocol_status: "compatible" | "insufficient_evidence" | "incompatible_protocol"
    protocol_issues: string[]
    hard_mismatches: string[]
  }
}

export type RunSnapshot = {
  runId: string | null
  status: "idle" | RunStatus
  resultState: ResultState | null
  cancelRequested: boolean
  completedPrompts: number
  totalPrompts: number
  currentPromptId: string | null
  currentPromptLabel: string | null
  selectedFingerprint: string
  topCandidate?: string
  similarityScore?: number
  failureReason?: string
}

export type WorkbenchState = {
  kind:
    | "empty"
    | "running"
    | "formal_result"
    | "provisional"
    | "insufficient_evidence"
    | "incompatible_protocol"
    | "configuration_error"
    | "stopped"
  title: string
  description: string
  completedPrompts?: number
  totalPrompts?: number
  currentPromptLabel?: string | null
  candidate?: string
  similarityScore?: number
}
