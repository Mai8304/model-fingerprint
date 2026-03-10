import type { RunSnapshot, WorkbenchState } from "@/lib/run-types"

export function deriveWorkbenchState(run: RunSnapshot): WorkbenchState {
  if (run.status === "idle") {
    return {
      kind: "empty",
      title: "No active check",
      description:
        "Enter endpoint details, choose a fingerprint model, and start a live five-prompt check.",
    }
  }

  if (run.status === "configuration_error") {
    return {
      kind: "configuration_error",
      title: "Unable to start check",
      description:
        run.failureReason ??
        "The endpoint configuration did not pass validation. Update the input fields and retry.",
    }
  }

  if (run.status === "stopped" || run.stoppedByUser) {
    return {
      kind: "stopped",
      title: "Check stopped",
      description: "This run was stopped before enough evidence was collected for a final conclusion.",
      completedPrompts: run.completedPrompts,
    }
  }

  if (run.status === "validating" || run.status === "running") {
    return {
      kind: "running",
      title: "Running model fingerprint check",
      description: "The workbench is collecting live evidence from the configured endpoint.",
    }
  }

  if (run.incompatibleProtocol) {
    return {
      kind: "incompatible_protocol",
      title: "Incompatible protocol",
      description:
        "The endpoint did not satisfy the expected response protocol consistently. This does not prove a model mismatch.",
      completedPrompts: run.completedPrompts,
    }
  }

  if (run.completedPrompts < 3) {
    return {
      kind: "insufficient_evidence",
      title: "Insufficient evidence",
      description:
        "The run finished with too little usable data to judge whether the endpoint matches the selected fingerprint.",
      completedPrompts: run.completedPrompts,
    }
  }

  if (run.completedPrompts < run.totalPrompts) {
    return {
      kind: "provisional",
      title: "Provisional observation",
      description:
        run.topCandidate === undefined
          ? "Partial evidence is available, but the run is incomplete and cannot support a final verdict."
          : `Partial evidence currently looks closer to ${run.topCandidate}. Treat this as a temporary observation, not a final conclusion.`,
      candidate: run.topCandidate,
      completedPrompts: run.completedPrompts,
    }
  }

  return {
    kind: "formal_result",
    title: "Formal conclusion",
    description:
      run.topCandidate === undefined
        ? "All prompts completed and the run is ready for a final comparison summary."
        : `All prompts completed. The endpoint can now be compared formally against ${run.selectedFingerprint}, with ${run.topCandidate} as the nearest candidate if applicable.`,
    completedPrompts: run.completedPrompts,
  }
}
