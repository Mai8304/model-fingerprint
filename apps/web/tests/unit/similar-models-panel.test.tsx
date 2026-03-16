import { render, screen, within } from "@testing-library/react"

import { SimilarModelsPanel } from "@/components/workbench/similar-models-panel"
import { Providers } from "@/components/providers"
import type { RunSnapshot } from "@/lib/run-types"

function buildRunSnapshot(): RunSnapshot {
  return {
    runId: "run_top5",
    status: "completed",
    resultState: "provisional",
    cancelRequested: false,
    completedPrompts: 4,
    failedPrompts: 0,
    totalPrompts: 5,
    currentPromptIndex: null,
    currentPromptId: null,
    currentPromptLabel: null,
    currentStageId: null,
    currentStageMessage: null,
    stages: [],
    prompts: [],
    selectedFingerprint: "Claude Sonnet 4.6",
    result: {
      run_id: "run_top5",
      result_state: "provisional",
      selected_fingerprint: {
        id: "claude-sonnet-4.6",
        label: "Claude Sonnet 4.6",
      },
      completed_prompts: 4,
      total_prompts: 5,
      verdict: "suspicious",
      summary: {
        similarity_score: 0.882,
        confidence_low: 0.972,
        confidence_high: 0.994,
        range_gap: 0.09,
        in_confidence_range: false,
        top_candidate_model_id: "claude-opus-4.1",
        top_candidate_label: "Claude Opus 4.1",
        top_candidate_similarity: 0.921,
        top2_candidate_model_id: "deepseek-chat",
        top2_candidate_label: "DeepSeek Chat",
        top2_candidate_similarity: 0.902,
        margin: 0.019,
        consistency: 0.91,
      },
      candidates: [
        {
          model_id: "claude-opus-4.1",
          label: "Claude Opus 4.1",
          similarity: 0.921,
          content_similarity: 0.91,
          capability_similarity: 0.95,
          consistency: 0.94,
          answer_coverage_ratio: 1,
          reasoning_coverage_ratio: 1,
          capability_coverage_ratio: 1,
          protocol_status: "compatible",
          protocol_issues: [],
          hard_mismatches: [],
        },
        {
          model_id: "deepseek-chat",
          label: "DeepSeek Chat",
          similarity: 0.902,
          content_similarity: 0.9,
          capability_similarity: 0.9,
          consistency: 0.9,
          answer_coverage_ratio: 1,
          reasoning_coverage_ratio: 1,
          capability_coverage_ratio: 1,
          protocol_status: "compatible",
          protocol_issues: [],
          hard_mismatches: [],
        },
        {
          model_id: "glm-5",
          label: "GLM-5",
          similarity: 0.891,
          content_similarity: 0.89,
          capability_similarity: 0.89,
          consistency: 0.89,
          answer_coverage_ratio: 1,
          reasoning_coverage_ratio: 1,
          capability_coverage_ratio: 1,
          protocol_status: "compatible",
          protocol_issues: [],
          hard_mismatches: [],
        },
        {
          model_id: "gpt-5.4",
          label: "GPT-5.4",
          similarity: 0.88,
          content_similarity: 0.88,
          capability_similarity: 0.88,
          consistency: 0.88,
          answer_coverage_ratio: 1,
          reasoning_coverage_ratio: 1,
          capability_coverage_ratio: 1,
          protocol_status: "compatible",
          protocol_issues: [],
          hard_mismatches: [],
        },
        {
          model_id: "gemini-3-pro-preview",
          label: "Gemini 3 Pro Preview",
          similarity: 0.871,
          content_similarity: 0.87,
          capability_similarity: 0.87,
          consistency: 0.87,
          answer_coverage_ratio: 1,
          reasoning_coverage_ratio: 1,
          capability_coverage_ratio: 1,
          protocol_status: "compatible",
          protocol_issues: [],
          hard_mismatches: [],
        },
        {
          model_id: "claude-sonnet-4.6",
          label: "Claude Sonnet 4.6",
          similarity: 0.812,
          content_similarity: 0.81,
          capability_similarity: 0.81,
          consistency: 0.81,
          answer_coverage_ratio: 1,
          reasoning_coverage_ratio: 1,
          capability_coverage_ratio: 1,
          protocol_status: "compatible",
          protocol_issues: [],
          hard_mismatches: [],
        },
      ],
      selected_candidate: {
        model_id: "claude-sonnet-4.6",
        label: "Claude Sonnet 4.6",
        similarity: 0.812,
        content_similarity: 0.81,
        capability_similarity: 0.81,
        consistency: 0.81,
        answer_coverage_ratio: 1,
        reasoning_coverage_ratio: 1,
        capability_coverage_ratio: 1,
        protocol_status: "compatible",
        protocol_issues: [],
        hard_mismatches: [],
      },
      dimensions: null,
      coverage: {
        answer_coverage_ratio: 1,
        reasoning_coverage_ratio: 1,
        capability_coverage_ratio: 1,
        protocol_status: "compatible",
      },
      diagnostics: {
        protocol_status: "compatible",
        protocol_issues: [],
        hard_mismatches: [],
        blocking_reasons: [],
        recommendations: [],
      },
      prompt_breakdown: [],
      capability_comparisons: [],
      thresholds_used: {
        match: 0.96,
        suspicious: 0.92,
        unknown: 0.8,
        margin: 0.02,
        consistency: 0.95,
        answer_min: 0.8,
        reasoning_min: 0.3,
      },
    },
  }
}

test("renders top 5 candidates and appends the selected fingerprint when it is outside top 5", () => {
  render(
    <Providers initialLocale="en">
      <SimilarModelsPanel run={buildRunSnapshot()} />
    </Providers>,
  )

  const panel = screen.getByRole("heading", { level: 3, name: "Similar Models (Top 5)" }).closest("section")
  expect(panel).not.toBeNull()

  const headers = within(panel as HTMLElement)
    .getAllByRole("columnheader")
    .map((header) => header.textContent)
  expect(headers).toEqual(["Rank", "Model", "Score"])

  expect(within(panel as HTMLElement).getByText("Claude Opus 4.1")).toBeInTheDocument()
  expect(within(panel as HTMLElement).getByText("0.921")).toBeInTheDocument()
  expect(within(panel as HTMLElement).getByText("Selected fingerprint")).toBeInTheDocument()
  expect(within(panel as HTMLElement).getByText("Claude Sonnet 4.6")).toBeInTheDocument()
  expect(within(panel as HTMLElement).getByText("0.812")).toBeInTheDocument()

  const cells = within(panel as HTMLElement).getAllByRole("cell")
  expect(cells.length).toBeGreaterThan(0)
  for (const cell of cells) {
    expect(cell).toHaveClass("align-middle")
    expect(cell).not.toHaveClass("align-top")
  }
})
