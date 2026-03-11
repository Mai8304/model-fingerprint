import type {
  ErrorCode,
  PromptStatus,
  ResultState,
  RunStage,
  RunStageStatus,
  RunStatus,
} from "@/lib/api-contract"

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

export type RemoteFieldName =
  | "apiKey"
  | "baseUrl"
  | "modelName"
  | "fingerprintModel"

export type RunStageResource = {
  id: RunStage
  status: RunStageStatus
  message: string | null
  started_at: string | null
  finished_at: string | null
}

export type RunPromptResource = {
  prompt_id: string
  status: PromptStatus
  elapsed_seconds: number | null
  elapsed_ms: number | null
  summary_code: string | null
  error_code: ErrorCode | null
  error_kind: string | null
  error_detail: string | null
  http_status: number | null
  started_at: string | null
  finished_at: string | null
  first_byte_ms: number | null
  bytes_received: number | null
  finish_reason: string | null
  parse_status: string | null
  answer_present: boolean | null
  reasoning_present: boolean | null
  scoreable: boolean | null
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
  current_stage_id: RunStage | null
  current_stage_message: string | null
  stages: RunStageResource[]
  progress: {
    completed_prompts: number
    failed_prompts: number
    total_prompts: number
    current_prompt_id: string | null
    current_prompt_index: number | null
    eta_seconds: number | null
  }
  prompts: RunPromptResource[]
  failure: {
    code: ErrorCode
    message: string | null
    retryable?: boolean | null
    http_status?: number | null
    field?: RemoteFieldName | null
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
    top_candidate_similarity: number | null
    top2_candidate_model_id: string | null
    top2_candidate_label: string | null
    top2_candidate_similarity: number | null
    margin: number | null
    consistency: number | null
  } | null
  candidates: Array<{
    model_id: string
    label: string
    similarity: number
    content_similarity: number | null
    capability_similarity: number | null
    consistency: number | null
    answer_coverage_ratio: number | null
    reasoning_coverage_ratio: number | null
    capability_coverage_ratio: number | null
    protocol_status: "compatible" | "insufficient_evidence" | "incompatible_protocol" | null
    protocol_issues: string[]
    hard_mismatches: string[]
  }>
  selected_candidate: {
    model_id: string
    label: string
    similarity: number
    content_similarity: number | null
    capability_similarity: number | null
    consistency: number | null
    answer_coverage_ratio: number | null
    reasoning_coverage_ratio: number | null
    capability_coverage_ratio: number | null
    protocol_status: "compatible" | "insufficient_evidence" | "incompatible_protocol" | null
    protocol_issues: string[]
    hard_mismatches: string[]
  } | null
  dimensions: {
    content_similarity: number | null
    capability_similarity: number | null
    answer_similarity: number | null
    reasoning_similarity: number | null
    transport_similarity: number | null
    surface_similarity: number | null
  } | null
  coverage: {
    answer_coverage_ratio: number
    reasoning_coverage_ratio: number
    capability_coverage_ratio: number
    protocol_status: "compatible" | "insufficient_evidence" | "incompatible_protocol"
  } | null
  diagnostics: {
    protocol_status: "compatible" | "insufficient_evidence" | "incompatible_protocol"
    protocol_issues: string[]
    hard_mismatches: string[]
    blocking_reasons: string[]
    recommendations: string[]
  }
  prompt_breakdown: Array<{
    prompt_id: string
    status: string
    similarity: number | null
    scoreable: boolean
    error_kind: string | null
    error_message: string | null
  }>
  thresholds_used: {
    match: number
    suspicious: number
    unknown: number
    margin: number
    consistency: number
    answer_min: number
    reasoning_min: number
  } | null
}

export type RunSnapshot = {
  runId: string | null
  status: "idle" | RunStatus
  resultState: ResultState | null
  cancelRequested: boolean
  createdAt?: string
  updatedAt?: string
  baseUrl?: string
  modelName?: string
  completedPrompts: number
  failedPrompts: number
  totalPrompts: number
  currentPromptIndex: number | null
  currentPromptId: string | null
  currentPromptLabel: string | null
  currentStageId: RunStage | null
  currentStageMessage: string | null
  stages: RunStageResource[]
  prompts: RunPromptResource[]
  selectedFingerprint: string
  topCandidate?: string
  similarityScore?: number
  failureCode?: ErrorCode
  failureReason?: string
  failureField?: RemoteFieldName | null
  result?: RunResultResource | null
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
