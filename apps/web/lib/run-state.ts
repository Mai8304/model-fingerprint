import type { LocaleKey } from "@/lib/i18n/messages"
import type { TranslationHelpers } from "@/lib/i18n/locale"
import { getPromptLabel } from "@/lib/prompt-copy"
import type { RunResource, RunResultResource, RunSnapshot, WorkbenchState } from "@/lib/run-types"

export function projectRunSnapshot(
  snapshot: RunResource | null,
  result: RunResultResource | null,
  options: {
    locale: LocaleKey
    failureReason?: string | null
  },
): RunSnapshot {
  if (snapshot === null) {
    if (options.failureReason) {
      return {
        runId: null,
        status: "configuration_error",
        resultState: "configuration_error",
        cancelRequested: false,
        failedPrompts: 0,
        currentPromptIndex: null,
        completedPrompts: 0,
        totalPrompts: 5,
        currentPromptId: null,
        currentPromptLabel: null,
        currentStageId: null,
        currentStageMessage: options.failureReason,
        stages: [],
        prompts: [],
        selectedFingerprint: "",
        failureCode: "INVALID_REQUEST",
        failureField: null,
        failureReason: options.failureReason,
        result: null,
      }
    }

    return {
      runId: null,
      status: "idle",
      resultState: null,
      cancelRequested: false,
      failedPrompts: 0,
      currentPromptIndex: null,
      completedPrompts: 0,
      totalPrompts: 5,
      currentPromptId: null,
      currentPromptLabel: null,
      currentStageId: null,
      currentStageMessage: null,
      stages: [],
      prompts: [],
      selectedFingerprint: "",
      result: null,
    }
  }

  const currentPromptId = snapshot.progress.current_prompt_id

  return {
    runId: snapshot.run_id,
    status: snapshot.run_status,
    resultState: result?.result_state ?? snapshot.result_state,
    cancelRequested: snapshot.cancel_requested,
    createdAt: snapshot.created_at,
    updatedAt: snapshot.updated_at,
    baseUrl: snapshot.input.base_url,
    modelName: snapshot.input.model_name,
    completedPrompts: result?.completed_prompts ?? snapshot.progress.completed_prompts,
    failedPrompts: snapshot.progress.failed_prompts,
    totalPrompts: result?.total_prompts ?? snapshot.progress.total_prompts,
    currentPromptIndex: snapshot.progress.current_prompt_index ?? null,
    currentPromptId,
    currentPromptLabel:
      currentPromptId === null ? null : getPromptLabel(currentPromptId, options.locale),
    currentStageId: snapshot.current_stage_id ?? null,
    currentStageMessage: snapshot.current_stage_message ?? null,
    stages: snapshot.stages ?? [],
    prompts: snapshot.prompts ?? [],
    selectedFingerprint:
      result?.selected_fingerprint.label ?? snapshot.input.fingerprint_model_id,
    topCandidate: result?.summary?.top_candidate_label ?? undefined,
    similarityScore: result?.summary?.similarity_score ?? undefined,
    failureCode: snapshot.failure?.code,
    failureReason: options.failureReason ?? snapshot.failure?.message ?? undefined,
    failureField: snapshot.failure?.field ?? null,
    result: result ?? null,
  }
}

export function deriveWorkbenchState(
  run: RunSnapshot,
  { t, format }: TranslationHelpers,
): WorkbenchState {
  if (run.status === "idle") {
    return {
      kind: "empty",
      title: t("state.empty.title"),
      description: t("state.empty.description"),
    }
  }

  if (run.status === "configuration_error") {
    return {
      kind: "configuration_error",
      title: t("state.configurationError.title"),
      description: run.failureReason ?? t("state.configurationError.description"),
    }
  }

  if (run.status === "stopped" || run.resultState === "stopped") {
    return {
      kind: "stopped",
      title: t("state.stopped.title"),
      description: t("state.stopped.description"),
      completedPrompts: run.completedPrompts,
      totalPrompts: run.totalPrompts,
    }
  }

  if (run.status === "validating" || run.status === "running") {
    return {
      kind: "running",
      title: t("state.running.title"),
      description: t("state.running.description"),
      completedPrompts: run.completedPrompts,
      totalPrompts: run.totalPrompts,
      currentPromptLabel: run.currentPromptLabel,
    }
  }

  if (run.resultState === "incompatible_protocol") {
    return {
      kind: "incompatible_protocol",
      title: t("state.incompatibleProtocol.title"),
      description: t("state.incompatibleProtocol.description"),
      completedPrompts: run.completedPrompts,
      totalPrompts: run.totalPrompts,
    }
  }

  if (
    run.resultState === "insufficient_evidence" ||
    (run.status === "completed" && run.completedPrompts < 3)
  ) {
    return {
      kind: "insufficient_evidence",
      title: t("state.insufficientEvidence.title"),
      description: t("state.insufficientEvidence.description"),
      completedPrompts: run.completedPrompts,
      totalPrompts: run.totalPrompts,
    }
  }

  if (
    run.resultState === "provisional" ||
    (run.status === "completed" && run.completedPrompts < run.totalPrompts)
  ) {
    return {
      kind: "provisional",
      title: t("state.provisional.title"),
      description:
        run.topCandidate === undefined
          ? t("state.provisional.description")
          : format("state.provisional.withCandidate", { candidate: run.topCandidate }),
      candidate: run.topCandidate,
      completedPrompts: run.completedPrompts,
      totalPrompts: run.totalPrompts,
      similarityScore: run.similarityScore,
    }
  }

  return {
    kind: "formal_result",
    title: t("state.formalResult.title"),
    description:
      run.topCandidate === undefined
        ? t("state.formalResult.description")
        : format("state.formalResult.withCandidate", {
            fingerprint: run.selectedFingerprint,
            candidate: run.topCandidate,
          }),
    completedPrompts: run.completedPrompts,
    totalPrompts: run.totalPrompts,
    similarityScore: run.similarityScore,
  }
}
