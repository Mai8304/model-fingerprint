import { render, screen } from "@testing-library/react"

import { PromptDiagnosticsTable } from "@/components/workbench/prompt-diagnostics-table"
import { Providers } from "@/components/providers"
import type { RunSnapshot } from "@/lib/run-types"

function buildRunSnapshot(): RunSnapshot {
  return {
    runId: "run_prompt_focus",
    status: "completed",
    resultState: "formal_result",
    cancelRequested: false,
    completedPrompts: 2,
    failedPrompts: 0,
    totalPrompts: 5,
    currentPromptIndex: null,
    currentPromptId: null,
    currentPromptLabel: null,
    currentStageId: null,
    currentStageMessage: null,
    stages: [],
    prompts: [
      {
        prompt_id: "p041",
        status: "completed",
        elapsed_seconds: 1.2,
        elapsed_ms: 1200,
        summary_code: null,
        error_code: null,
        error_kind: null,
        error_detail: null,
        http_status: null,
        started_at: null,
        finished_at: null,
        first_byte_ms: null,
        bytes_received: null,
        finish_reason: null,
        parse_status: null,
        answer_present: true,
        reasoning_present: true,
        scoreable: true,
      },
      {
        prompt_id: "p042",
        status: "running",
        elapsed_seconds: 0.8,
        elapsed_ms: 800,
        summary_code: null,
        error_code: null,
        error_kind: null,
        error_detail: null,
        http_status: null,
        started_at: null,
        finished_at: null,
        first_byte_ms: null,
        bytes_received: null,
        finish_reason: null,
        parse_status: null,
        answer_present: null,
        reasoning_present: null,
        scoreable: null,
      },
    ],
    selectedFingerprint: "GLM-5",
    result: {
      run_id: "run_prompt_focus",
      result_state: "formal_result",
      selected_fingerprint: {
        id: "glm-5",
        label: "GLM-5",
      },
      completed_prompts: 2,
      total_prompts: 5,
      verdict: "match",
      summary: null,
      candidates: [],
      selected_candidate: null,
      dimensions: null,
      coverage: null,
      diagnostics: {
        protocol_status: "compatible",
        protocol_issues: [],
        hard_mismatches: [],
        blocking_reasons: [],
        recommendations: [],
      },
      prompt_breakdown: [
        {
          prompt_id: "p041",
          status: "completed",
          similarity: 0.972,
          scoreable: true,
          error_kind: null,
          error_message: null,
        },
      ],
      capability_comparisons: [],
      thresholds_used: null,
    },
  }
}

test("renders stable focus copy instead of repeating similarity text", () => {
  render(
    <Providers initialLocale="zh-CN">
      <PromptDiagnosticsTable run={buildRunSnapshot()} />
    </Providers>,
  )

  expect(screen.getByText("测评重点")).toBeInTheDocument()
  expect(screen.getByText("Prompt 1")).toBeInTheDocument()
  expect(screen.getByText("Prompt 2")).toBeInTheDocument()
  expect(screen.getByText("复杂线索下的责任归因能力")).toBeInTheDocument()
  expect(screen.getByText("相近名称的实体筛选能力")).toBeInTheDocument()
  expect(screen.queryByText("相似度: 0.972")).not.toBeInTheDocument()
})
