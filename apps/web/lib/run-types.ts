export type RunLifecycleStatus =
  | "idle"
  | "validating"
  | "running"
  | "completed"
  | "configuration_error"
  | "stopped"

export type RunSnapshot = {
  status: RunLifecycleStatus
  completedPrompts: number
  totalPrompts: number
  incompatibleProtocol: boolean
  stoppedByUser: boolean
  selectedFingerprint: string
  topCandidate?: string
  similarityScore?: number
  confidenceLow?: number
  confidenceHigh?: number
  failureReason?: string
}

export type WorkbenchState =
  | {
      kind: "empty"
      title: string
      description: string
    }
  | {
      kind: "running"
      title: string
      description: string
    }
  | {
      kind: "formal_result"
      title: string
      description: string
      completedPrompts: number
    }
  | {
      kind: "provisional"
      title: string
      description: string
      candidate?: string
      completedPrompts: number
    }
  | {
      kind: "insufficient_evidence"
      title: string
      description: string
      completedPrompts: number
    }
  | {
      kind: "incompatible_protocol"
      title: string
      description: string
      completedPrompts: number
    }
  | {
      kind: "configuration_error"
      title: string
      description: string
    }
  | {
      kind: "stopped"
      title: string
      description: string
      completedPrompts: number
    }
