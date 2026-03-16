import { render, screen } from "@testing-library/react"

import {
  ConclusionPanel,
  DetailedDiagnosticsPanel,
} from "@/components/workbench/conclusion-panel"
import { Providers } from "@/components/providers"
import type { RunSnapshot } from "@/lib/run-types"

function buildRunSnapshot(): RunSnapshot {
  return {
    runId: "run_zh_localized",
    status: "completed",
    resultState: "formal_result",
    cancelRequested: false,
    completedPrompts: 5,
    failedPrompts: 0,
    totalPrompts: 5,
    currentPromptIndex: null,
    currentPromptId: null,
    currentPromptLabel: null,
    currentStageId: null,
    currentStageMessage: null,
    stages: [],
    prompts: [],
    selectedFingerprint: "GLM-5",
    result: {
      run_id: "run_zh_localized",
      result_state: "formal_result",
      selected_fingerprint: {
        id: "glm-5",
        label: "GLM-5",
      },
      completed_prompts: 5,
      total_prompts: 5,
      verdict: "mismatch",
      summary: {
        similarity_score: 0.834,
        confidence_low: 0.972,
        confidence_high: 0.994,
        range_gap: 0.138,
        in_confidence_range: false,
        top_candidate_model_id: "deepseek-chat",
        top_candidate_label: "DeepSeek Chat",
        top_candidate_similarity: 0.901,
        top2_candidate_model_id: "glm-5",
        top2_candidate_label: "GLM-5",
        top2_candidate_similarity: 0.834,
        margin: 0.067,
        consistency: 0.91,
      },
      candidates: [],
      selected_candidate: {
        model_id: "glm-5",
        label: "GLM-5",
        similarity: 0.834,
        content_similarity: 0.83,
        capability_similarity: 0.9,
        consistency: 0.91,
        answer_coverage_ratio: 1,
        reasoning_coverage_ratio: 0,
        capability_coverage_ratio: 1,
        protocol_status: "incompatible_protocol",
        protocol_issues: ["reasoning coverage is below the profile expectation"],
        hard_mismatches: [],
      },
      dimensions: null,
      coverage: {
        answer_coverage_ratio: 1,
        reasoning_coverage_ratio: 0,
        capability_coverage_ratio: 1,
        protocol_status: "incompatible_protocol",
      },
      diagnostics: {
        protocol_status: "incompatible_protocol",
        protocol_issues: ["reasoning coverage is below the profile expectation"],
        hard_mismatches: [],
        blocking_reasons: ["reasoning coverage is below the profile expectation"],
        recommendations: [
          "The selected fingerprint is not the closest candidate. Inspect DeepSeek Chat as the nearest match.",
        ],
      },
      prompt_breakdown: [
        {
          prompt_id: "p021",
          status: "completed",
          similarity: 0.881,
          scoreable: true,
          error_kind: null,
          error_message: null,
        },
        {
          prompt_id: "p022",
          status: "completed",
          similarity: 0.883,
          scoreable: true,
          error_kind: null,
          error_message: null,
        },
        {
          prompt_id: "p023",
          status: "completed",
          similarity: 0.68,
          scoreable: true,
          error_kind: null,
          error_message: null,
        },
      ],
      capability_comparisons: [
        {
          capability: "thinking",
          observed_status: "accepted_but_ignored",
          expected_status: "accepted_but_ignored",
          is_consistent: true,
        },
        {
          capability: "tools",
          observed_status: "supported",
          expected_status: "supported",
          is_consistent: true,
        },
        {
          capability: "image",
          observed_status: "supported",
          expected_status: "unsupported",
          is_consistent: false,
        },
      ],
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

test("localizes conclusion diagnostics and prompt names in simplified chinese", () => {
  const run = buildRunSnapshot()

  render(
    <Providers initialLocale="zh-CN">
      <ConclusionPanel run={run} />
      <DetailedDiagnosticsPanel run={run} />
    </Providers>,
  )

  expect(screen.getByText("分析模型证据判断能力：相似度 0.881。")).toBeInTheDocument()
  expect(screen.getByText("分析模型上下文检索能力：相似度 0.883。")).toBeInTheDocument()
  expect(screen.getByText("分析模型审慎作答能力：相似度 0.680。")).toBeInTheDocument()
  expect(screen.getByText("Thinking：一致（请求已接受，但能力未生效）")).toBeInTheDocument()
  expect(screen.getByText("Tools：一致（支持）")).toBeInTheDocument()
  expect(
    screen.getByText("Image：不一致（测试模型：支持；指纹期望：不支持）"),
  ).toBeInTheDocument()
  expect(screen.queryByText(/p021|p022|p023/)).not.toBeInTheDocument()

  expect(screen.getAllByText("推理覆盖度低于指纹画像的预期值。").length).toBeGreaterThan(0)
  expect(
    screen.getByText("所选指纹不是最接近候选，请重点检查 DeepSeek Chat。"),
  ).toBeInTheDocument()
  expect(screen.getByText("最接近候选")).toBeInTheDocument()
  expect(
    screen.getByText(
      (_content, element) => element?.textContent === "DeepSeek Chat (0.901)",
    ),
  ).toBeInTheDocument()
  expect(
    screen.queryByText(
      "The selected fingerprint is not the closest candidate. Inspect DeepSeek Chat as the nearest match.",
    ),
  ).not.toBeInTheDocument()
  expect(
    screen.queryByText("reasoning coverage is below the profile expectation"),
  ).not.toBeInTheDocument()
  expect(screen.queryByText("观测相似度")).not.toBeInTheDocument()
  expect(screen.queryByText("领先差值")).not.toBeInTheDocument()
  expect(screen.queryByText("一致性")).not.toBeInTheDocument()
  expect(screen.queryByText("答案覆盖度")).not.toBeInTheDocument()
  expect(screen.queryByText("推理覆盖度")).not.toBeInTheDocument()
})

test("replaces raw endpoint probe errors with a user-facing configuration error message", () => {
  const run: RunSnapshot = {
    runId: "run_zh_config_error",
    status: "configuration_error",
    resultState: "configuration_error",
    cancelRequested: false,
    completedPrompts: 0,
    failedPrompts: 0,
    totalPrompts: 5,
    currentPromptIndex: null,
    currentPromptId: null,
    currentPromptLabel: null,
    currentStageId: "capability_probe",
    currentStageMessage: "<urlopen error [Errno -2] Name or service not known>",
    stages: [],
    prompts: [],
    selectedFingerprint: "GLM-5",
    failureCode: "ENDPOINT_UNREACHABLE",
    failureReason:
      "<urlopen error [Errno -2] Name or service not known> | <urlopen error [Errno -2] Name or service not known>",
    failureField: "baseUrl",
    result: null,
  }

  render(
    <Providers initialLocale="zh-CN">
      <ConclusionPanel run={run} />
    </Providers>,
  )

  expect(screen.getByText("配置错误")).toBeInTheDocument()
  expect(
    screen.getByText("当前接口无法连接，请检查 Base URL、域名解析和网络可达性。"),
  ).toBeInTheDocument()
  expect(
    screen.queryByText(/Name or service not known|urlopen error/i),
  ).not.toBeInTheDocument()
})

test("renders mismatch nearest candidate as a standalone block below the first sentence", () => {
  const run: RunSnapshot = {
    runId: "run_candidate_bold",
    status: "completed",
    resultState: "formal_result",
    cancelRequested: false,
    completedPrompts: 5,
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
      run_id: "run_candidate_bold",
      result_state: "formal_result",
      selected_fingerprint: {
        id: "claude-sonnet-4.6",
        label: "Claude Sonnet 4.6",
      },
      completed_prompts: 5,
      total_prompts: 5,
      verdict: "mismatch",
      summary: {
        similarity_score: 0.882,
        confidence_low: 0.972,
        confidence_high: 0.994,
        range_gap: 0.09,
        in_confidence_range: false,
        top_candidate_model_id: "claude-opus-4.1",
        top_candidate_label: "Claude Opus 4.1",
        top_candidate_similarity: 0.921,
        top2_candidate_model_id: "claude-sonnet-4.6",
        top2_candidate_label: "Claude Sonnet 4.6",
        top2_candidate_similarity: 0.882,
        margin: 0.039,
        consistency: 0.95,
      },
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

  render(
    <Providers initialLocale="zh-CN">
      <ConclusionPanel run={run} />
    </Providers>,
  )

  expect(screen.getByText("测试模型与所选指纹模型不一致，更可能属于其他候选模型。")).toBeInTheDocument()
  expect(screen.getByText("最接近候选")).toBeInTheDocument()
  expect(
    screen.getByText(
      (_content, element) => element?.textContent === "Claude Opus 4.1 (0.921)",
    ),
  ).toBeInTheDocument()
  expect(screen.getByText("Claude Opus 4.1", { selector: "strong" })).toBeInTheDocument()
  expect(screen.queryByText(/最接近候选为 Claude Opus 4.1/)).not.toBeInTheDocument()
})

test("renders highly consistent conclusion with only the selected fingerprint model bolded in the sentence", () => {
  const run: RunSnapshot = {
    runId: "run_highly_consistent_sentence",
    status: "completed",
    resultState: "formal_result",
    cancelRequested: false,
    completedPrompts: 5,
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
      run_id: "run_highly_consistent_sentence",
      result_state: "formal_result",
      selected_fingerprint: {
        id: "claude-sonnet-4.6",
        label: "Claude Sonnet 4.6",
      },
      completed_prompts: 5,
      total_prompts: 5,
      verdict: "match",
      summary: {
        similarity_score: 0.985,
        confidence_low: 0.972,
        confidence_high: 0.994,
        range_gap: 0,
        in_confidence_range: true,
        top_candidate_model_id: "claude-sonnet-4.6",
        top_candidate_label: "Claude Sonnet 4.6",
        top_candidate_similarity: 0.985,
        top2_candidate_model_id: "claude-opus-4.1",
        top2_candidate_label: "Claude Opus 4.1",
        top2_candidate_similarity: 0.921,
        margin: 0.064,
        consistency: 0.996,
      },
      candidates: [],
      selected_candidate: null,
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

  render(
    <Providers initialLocale="zh-CN">
      <ConclusionPanel run={run} />
    </Providers>,
  )

  expect(
    screen.getByText(
      (_content, element) =>
        element?.tagName === "P" &&
        element.textContent === "测试模型与所选指纹模型 Claude Sonnet 4.6 高度一致。",
    ),
  ).toBeInTheDocument()
  expect(screen.getByText("Claude Sonnet 4.6", { selector: "strong" })).toBeInTheDocument()
  expect(screen.queryByText("最接近候选")).not.toBeInTheDocument()
})
