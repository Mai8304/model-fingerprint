import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, vi } from "vitest"

import { DetectionConsole } from "@/components/detection-console"
import { Providers } from "@/components/providers"

function promptResource(
  prompt_id: string,
  status: string,
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    prompt_id,
    status,
    elapsed_seconds: null,
    elapsed_ms: null,
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
    ...overrides,
  }
}

function stageResource(
  id: string,
  status: string,
  message: string | null,
  overrides: Partial<Record<string, unknown>> = {},
) {
  return {
    id,
    status,
    message,
    started_at: "2026-03-10T15:30:00Z",
    finished_at: status === "completed" ? "2026-03-10T15:30:05Z" : null,
    ...overrides,
  }
}

function jsonResponse(payload: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(payload), {
    headers: {
      "content-type": "application/json",
    },
    ...init,
  })
}

function delayedJsonResponse(
  payload: unknown,
  delayMs: number,
  init: ResponseInit = {},
) {
  return new Promise<Response>((resolve) => {
    setTimeout(() => {
      resolve(jsonResponse(payload, init))
    }, delayMs)
  })
}

function renderConsole() {
  render(
    <Providers initialLocale="en">
      <DetectionConsole />
    </Providers>,
  )
}

async function flushAsyncWork() {
  await act(async () => {
    await Promise.resolve()
  })
}

async function advancePolling(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms)
  })
}

function fillAndSubmitForm() {
  fireEvent.change(screen.getByLabelText("API Key"), {
    target: { value: "sk-live" },
  })
  fireEvent.change(screen.getByLabelText("Base URL"), {
    target: { value: "https://api.example.com/v1" },
  })
  fireEvent.change(screen.getByLabelText("Model Name"), {
    target: { value: "gpt-4o-mini" },
  })
  fireEvent.change(screen.getByLabelText("Fingerprint Model"), {
    target: { value: "glm-5" },
  })
  fireEvent.click(screen.getByRole("button", { name: "Start Check" }))
}

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

test("loads registry, submits a run, polls progress, and renders the approved formal result blocks", async () => {
  const fetchMock = vi.fn()
  fetchMock
    .mockResolvedValueOnce(
      jsonResponse({
        items: [
          {
            id: "deepseek-chat",
            label: "DeepSeek Chat",
            suite_id: "fingerprint-suite-v3",
            available: true,
            image_generation: { status: "unsupported", confidence: 1 },
            vision_understanding: { status: "unsupported", confidence: 1 },
          },
          {
            id: "glm-5",
            label: "GLM-5",
            suite_id: "fingerprint-suite-v3",
            available: true,
            image_generation: { status: "unsupported", confidence: 1 },
            vision_understanding: { status: "unsupported", confidence: 1 },
          },
        ],
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          run_id: "run_123",
          run_status: "validating",
          result_state: null,
          cancel_requested: false,
        },
        { status: 201 },
      ),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_123",
        run_status: "validating",
        result_state: null,
        cancel_requested: false,
        created_at: "2026-03-10T15:30:00Z",
        updated_at: "2026-03-10T15:30:00Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        current_stage_id: "config_validation",
        current_stage_message: "validating endpoint configuration",
        stages: [
          stageResource("config_validation", "running", "validating endpoint configuration", {
            finished_at: null,
          }),
          stageResource("endpoint_resolution", "pending", null, { started_at: null, finished_at: null }),
          stageResource("capability_probe", "pending", null, { started_at: null, finished_at: null }),
          stageResource("prompt_execution", "pending", null, { started_at: null, finished_at: null }),
          stageResource("comparison", "pending", null, { started_at: null, finished_at: null }),
        ],
        progress: {
          completed_prompts: 0,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: null,
          current_prompt_index: null,
          eta_seconds: null,
        },
        prompts: [
          promptResource("p021", "pending"),
          promptResource("p022", "pending"),
          promptResource("p023", "pending"),
          promptResource("p024", "pending"),
          promptResource("p025", "pending"),
        ],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_123",
        run_status: "running",
        result_state: null,
        cancel_requested: false,
        created_at: "2026-03-10T15:30:00Z",
        updated_at: "2026-03-10T15:30:10Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        current_stage_id: "prompt_execution",
        current_stage_message: "running prompt p023",
        stages: [
          stageResource("config_validation", "completed", "configuration accepted"),
          stageResource("endpoint_resolution", "completed", "resolved endpoint profile"),
          stageResource(
            "capability_probe",
            "completed",
            "capability probe completed: thinking=supported, tools=accepted_but_ignored, streaming=supported, image_generation=supported, vision_understanding=accepted_but_ignored",
          ),
          stageResource("prompt_execution", "running", "running prompt p023", {
            finished_at: null,
          }),
          stageResource("comparison", "pending", null, { started_at: null, finished_at: null }),
        ],
        progress: {
          completed_prompts: 2,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: "p023",
          current_prompt_index: 3,
          eta_seconds: 45,
        },
        prompts: [
          promptResource("p021", "completed", {
            elapsed_seconds: 8,
            elapsed_ms: 8012,
            summary_code: "scoreable",
            parse_status: "parsed",
            answer_present: true,
            reasoning_present: false,
            scoreable: true,
            started_at: "2026-03-10T15:30:06Z",
            finished_at: "2026-03-10T15:30:14Z",
          }),
          promptResource("p022", "completed", {
            elapsed_seconds: 9,
            elapsed_ms: 9140,
            summary_code: "scoreable",
            parse_status: "parsed",
            answer_present: true,
            reasoning_present: false,
            scoreable: true,
            started_at: "2026-03-10T15:30:14Z",
            finished_at: "2026-03-10T15:30:23Z",
          }),
          promptResource("p023", "running", {
            elapsed_seconds: 4,
            elapsed_ms: 4200,
            started_at: "2026-03-10T15:30:23Z",
          }),
          promptResource("p024", "pending"),
          promptResource("p025", "pending"),
        ],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_123",
        run_status: "completed",
        result_state: "formal_result",
        cancel_requested: false,
        created_at: "2026-03-10T15:30:00Z",
        updated_at: "2026-03-10T15:30:30Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        current_stage_id: "comparison",
        current_stage_message: "generating final comparison",
        stages: [
          stageResource("config_validation", "completed", "configuration accepted"),
          stageResource("endpoint_resolution", "completed", "resolved endpoint profile"),
          stageResource(
            "capability_probe",
            "completed",
            "capability probe completed: thinking=supported, tools=accepted_but_ignored, streaming=supported, image_generation=supported, vision_understanding=accepted_but_ignored",
          ),
          stageResource("prompt_execution", "completed", "all prompts completed"),
          stageResource("comparison", "running", "generating final comparison", {
            finished_at: null,
          }),
        ],
        progress: {
          completed_prompts: 5,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: null,
          current_prompt_index: null,
          eta_seconds: 0,
        },
        prompts: [
          promptResource("p021", "completed", {
            elapsed_seconds: 8,
            elapsed_ms: 8012,
            summary_code: "scoreable",
            parse_status: "parsed",
            answer_present: true,
            reasoning_present: false,
            scoreable: true,
          }),
          promptResource("p022", "completed", {
            elapsed_seconds: 9,
            elapsed_ms: 9140,
            summary_code: "scoreable",
            parse_status: "parsed",
            answer_present: true,
            reasoning_present: false,
            scoreable: true,
          }),
          promptResource("p023", "completed", {
            elapsed_seconds: 7,
            elapsed_ms: 7025,
            summary_code: "scoreable",
            parse_status: "parsed",
            answer_present: true,
            reasoning_present: false,
            scoreable: true,
          }),
          promptResource("p024", "completed", {
            elapsed_seconds: 6,
            elapsed_ms: 6122,
            summary_code: "scoreable",
            parse_status: "parsed",
            answer_present: true,
            reasoning_present: false,
            scoreable: true,
          }),
          promptResource("p025", "completed", {
            elapsed_seconds: 7,
            elapsed_ms: 7333,
            summary_code: "scoreable",
            parse_status: "parsed",
            answer_present: true,
            reasoning_present: false,
            scoreable: true,
          }),
        ],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_123",
        result_state: "formal_result",
        selected_fingerprint: {
          id: "glm-5",
          label: "GLM-5",
        },
        completed_prompts: 5,
        total_prompts: 5,
        verdict: "match",
        summary: {
          similarity_score: 0.985,
          confidence_low: 0.982,
          confidence_high: 0.994,
          range_gap: 0,
          in_confidence_range: true,
          top_candidate_model_id: "glm-5",
          top_candidate_label: "GLM-5",
          top_candidate_similarity: 0.985,
          top2_candidate_model_id: "deepseek-chat",
          top2_candidate_label: "DeepSeek Chat",
          top2_candidate_similarity: 0.921,
          margin: 0.064,
          consistency: 0.996,
        },
        selected_candidate: {
          model_id: "glm-5",
          label: "GLM-5",
          similarity: 0.985,
          content_similarity: 0.982,
          capability_similarity: 1,
          consistency: 0.996,
          answer_coverage_ratio: 1,
          reasoning_coverage_ratio: 1,
          capability_coverage_ratio: 1,
          protocol_status: "compatible",
          protocol_issues: [],
          hard_mismatches: [],
        },
        candidates: [
          {
            model_id: "glm-5",
            label: "GLM-5",
            similarity: 0.985,
            content_similarity: 0.982,
            capability_similarity: 1,
            consistency: 0.996,
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
            similarity: 0.921,
            content_similarity: 0.918,
            capability_similarity: 1,
            consistency: 0.972,
            answer_coverage_ratio: 1,
            reasoning_coverage_ratio: 1,
            capability_coverage_ratio: 1,
            protocol_status: "compatible",
            protocol_issues: [],
            hard_mismatches: [],
          },
        ],
        capability_comparisons: [
          {
            capability: "thinking",
            observed_status: "supported",
            expected_status: "supported",
            is_consistent: true,
          },
          {
            capability: "tools",
            observed_status: "supported",
            expected_status: "supported",
            is_consistent: true,
          },
          {
            capability: "streaming",
            observed_status: "unsupported",
            expected_status: "unsupported",
            is_consistent: true,
          },
          {
            capability: "image_generation",
            observed_status: "supported",
            expected_status: "supported",
            is_consistent: true,
          },
          {
            capability: "vision_understanding",
            observed_status: "accepted_but_ignored",
            expected_status: "accepted_but_ignored",
            is_consistent: true,
          },
        ],
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
          recommendations: ["No follow-up action is required for this run."],
        },
        prompt_breakdown: [
          {
            prompt_id: "p021",
            status: "completed",
            similarity: 0.992,
            scoreable: true,
            error_kind: null,
            error_message: null,
          },
          {
            prompt_id: "p022",
            status: "completed",
            similarity: 0.988,
            scoreable: true,
            error_kind: null,
            error_message: null,
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
      }),
    )

  vi.stubGlobal("fetch", fetchMock)
  renderConsole()
  await flushAsyncWork()

  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(screen.queryByText("Fingerprint Capability Matrix")).not.toBeInTheDocument()

  fillAndSubmitForm()
  await flushAsyncWork()

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/runs",
    expect.objectContaining({
      method: "POST",
    }),
  )

  await advancePolling(1000)
  expect(screen.getAllByText("2 / 5").length).toBeGreaterThan(0)
  expect(screen.getByText("Conclusion In Progress")).toBeInTheDocument()
  expect(screen.queryByText("Prompt comparison data is not available yet.")).not.toBeInTheDocument()
  expect(screen.queryByText("Capability comparison data is not available yet.")).not.toBeInTheDocument()
  expect(screen.getByText("Evidence Judgment")).toBeInTheDocument()
  expect(screen.getByText("Question 3")).toBeInTheDocument()
  expect(
    screen.getAllByText("Request accepted, but capability did not take effect").length,
  ).toBeGreaterThan(0)
  expect(screen.queryByText("p021")).not.toBeInTheDocument()

  await advancePolling(1000)
  expect(screen.getByText("✅ Formal Conclusion · Highly Consistent")).toBeInTheDocument()
  expect(
    screen.getByText(
      (_content, element) =>
        element?.tagName === "P" &&
        element.textContent === "The tested model is highly consistent with the selected fingerprint model GLM-5.",
    ),
  ).toBeInTheDocument()
  expect(screen.getByText("GLM-5", { selector: "strong" })).toBeInTheDocument()
  expect(screen.queryByText("Nearest Candidate")).not.toBeInTheDocument()
  expect(screen.getByText("Capability Probe")).toBeInTheDocument()
  expect(screen.getByText("Prompt Probe")).toBeInTheDocument()
  expect(screen.getByText("Detailed Diagnostics")).toBeInTheDocument()
  expect(screen.getByText("Similar Models (Top 5)")).toBeInTheDocument()
  expect(screen.getAllByText("0.982 - 0.994").length).toBeGreaterThan(0)
  expect(screen.getByText("Thinking")).toBeInTheDocument()
  expect(screen.getByText("Chain of thought")).toBeInTheDocument()
  expect(screen.getAllByText("Image").length).toBeGreaterThan(0)
  expect(screen.getAllByText("Vision").length).toBeGreaterThan(0)
  expect(screen.getAllByText("Image generation").length).toBeGreaterThan(0)
  expect(screen.getAllByText("Visual understanding").length).toBeGreaterThan(0)
  expect(screen.getByText("No follow-up action is required for this run.")).toBeInTheDocument()
  expect(screen.queryByText("Observed Similarity")).not.toBeInTheDocument()
  expect(screen.queryByText("Margin")).not.toBeInTheDocument()
  expect(screen.queryByText("Consistency")).not.toBeInTheDocument()
  expect(screen.queryByText("Answer Coverage")).not.toBeInTheDocument()
  expect(screen.queryByText("Reasoning Coverage")).not.toBeInTheDocument()
})

test("renders insufficient-evidence output from the terminal result contract", async () => {
  const fetchMock = vi.fn()
  fetchMock
    .mockResolvedValueOnce(
      jsonResponse({
        items: [{ id: "glm-5", label: "GLM-5", suite_id: "fingerprint-suite-v3", available: true }],
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          run_id: "run_456",
          run_status: "validating",
          result_state: null,
          cancel_requested: false,
        },
        { status: 201 },
      ),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_456",
        run_status: "validating",
        result_state: null,
        cancel_requested: false,
        created_at: "2026-03-10T15:35:00Z",
        updated_at: "2026-03-10T15:35:00Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        progress: {
          completed_prompts: 0,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: null,
          eta_seconds: null,
        },
        prompts: [],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_456",
        run_status: "completed",
        result_state: "insufficient_evidence",
        cancel_requested: false,
        created_at: "2026-03-10T15:35:00Z",
        updated_at: "2026-03-10T15:35:20Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        progress: {
          completed_prompts: 2,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: null,
          eta_seconds: 0,
        },
        prompts: [],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_456",
        result_state: "insufficient_evidence",
        selected_fingerprint: {
          id: "glm-5",
          label: "GLM-5",
        },
        completed_prompts: 2,
        total_prompts: 5,
        verdict: null,
        summary: null,
        candidates: [],
        diagnostics: {
          protocol_status: "insufficient_evidence",
          protocol_issues: [],
          hard_mismatches: [],
        },
      }),
    )

  vi.stubGlobal("fetch", fetchMock)
  renderConsole()
  await flushAsyncWork()
  expect(fetchMock).toHaveBeenCalledTimes(1)
  fillAndSubmitForm()
  await flushAsyncWork()

  await advancePolling(1000)
  expect(screen.getAllByText("Insufficient Evidence").length).toBeGreaterThan(0)
})

test("stops an active run through the cancel endpoint", async () => {
  const fetchMock = vi.fn()
  fetchMock
    .mockResolvedValueOnce(
      jsonResponse({
        items: [{ id: "glm-5", label: "GLM-5", suite_id: "fingerprint-suite-v3", available: true }],
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          run_id: "run_789",
          run_status: "validating",
          result_state: null,
          cancel_requested: false,
        },
        { status: 201 },
      ),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_789",
        run_status: "validating",
        result_state: null,
        cancel_requested: false,
        created_at: "2026-03-10T15:40:00Z",
        updated_at: "2026-03-10T15:40:00Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        progress: {
          completed_prompts: 0,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: null,
          eta_seconds: null,
        },
        prompts: [],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_789",
        run_status: "running",
        result_state: null,
        cancel_requested: false,
        created_at: "2026-03-10T15:40:00Z",
        updated_at: "2026-03-10T15:40:08Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        progress: {
          completed_prompts: 1,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: "p022",
          eta_seconds: 50,
        },
        prompts: [],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          run_id: "run_789",
          run_status: "running",
          result_state: null,
          cancel_requested: true,
        },
        { status: 202 },
      ),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_789",
        run_status: "stopped",
        result_state: "stopped",
        cancel_requested: true,
        created_at: "2026-03-10T15:40:00Z",
        updated_at: "2026-03-10T15:40:20Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        progress: {
          completed_prompts: 1,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: null,
          eta_seconds: 0,
        },
        prompts: [],
        failure: null,
      }),
    )

  vi.stubGlobal("fetch", fetchMock)
  renderConsole()
  await flushAsyncWork()
  expect(fetchMock).toHaveBeenCalledTimes(1)
  fillAndSubmitForm()
  await flushAsyncWork()

  await advancePolling(1000)
  fireEvent.click(screen.getByRole("button", { name: "Stop Check" }))
  await flushAsyncWork()

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/runs/run_789/cancel",
    expect.objectContaining({
      method: "POST",
    }),
  )

  await advancePolling(1000)
  expect(screen.getByText("Check Stopped")).toBeInTheDocument()
})

test("keeps the second-run error visible instead of reviving the previous completed report", async () => {
  const completedSnapshot = {
    run_id: "run_prev",
    run_status: "completed",
    result_state: "formal_result",
    cancel_requested: false,
    created_at: "2026-03-10T16:00:00Z",
    updated_at: "2026-03-10T16:00:20Z",
    input: {
      base_url: "https://api.example.com/v1",
      model_name: "gpt-4o-mini",
      fingerprint_model_id: "glm-5",
    },
    current_stage_id: "comparison",
    current_stage_message: "comparison completed",
    stages: [
      stageResource("config_validation", "completed", "configuration accepted"),
      stageResource("endpoint_resolution", "completed", "resolved endpoint profile"),
      stageResource("capability_probe", "completed", "capability probe completed: thinking=supported"),
      stageResource("prompt_execution", "completed", "all prompts completed"),
      stageResource("comparison", "completed", "comparison completed"),
    ],
    progress: {
      completed_prompts: 5,
      failed_prompts: 0,
      total_prompts: 5,
      current_prompt_id: null,
      current_prompt_index: null,
      eta_seconds: 0,
    },
    prompts: [
      promptResource("p021", "completed", { scoreable: true }),
      promptResource("p022", "completed", { scoreable: true }),
      promptResource("p023", "completed", { scoreable: true }),
      promptResource("p024", "completed", { scoreable: true }),
      promptResource("p025", "completed", { scoreable: true }),
    ],
    failure: null,
  }

  const completedResult = {
    run_id: "run_prev",
    result_state: "formal_result",
    selected_fingerprint: {
      id: "glm-5",
      label: "GLM-5",
    },
    completed_prompts: 5,
    total_prompts: 5,
    verdict: "match",
    summary: {
      similarity_score: 0.985,
      confidence_low: 0.982,
      confidence_high: 0.994,
      range_gap: 0,
      in_confidence_range: true,
      top_candidate_model_id: "glm-5",
      top_candidate_label: "GLM-5",
      top_candidate_similarity: 0.985,
      top2_candidate_model_id: "deepseek-chat",
      top2_candidate_label: "DeepSeek Chat",
      top2_candidate_similarity: 0.921,
      margin: 0.064,
      consistency: 0.996,
    },
    selected_candidate: {
      model_id: "glm-5",
      label: "GLM-5",
      similarity: 0.985,
      content_similarity: 0.982,
      capability_similarity: 1,
      consistency: 0.996,
      answer_coverage_ratio: 1,
      reasoning_coverage_ratio: 1,
      capability_coverage_ratio: 1,
      protocol_status: "compatible",
      protocol_issues: [],
      hard_mismatches: [],
    },
    candidates: [],
    capability_comparisons: [],
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
    prompt_breakdown: [
      { prompt_id: "p021", status: "completed", similarity: 0.99, scoreable: true, error_kind: null, error_message: null },
      { prompt_id: "p022", status: "completed", similarity: 0.98, scoreable: true, error_kind: null, error_message: null },
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
  }

  const fetchMock = vi.fn()
  fetchMock
    .mockResolvedValueOnce(
      jsonResponse({
        items: [{ id: "glm-5", label: "GLM-5", suite_id: "fingerprint-suite-v3", available: true }],
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse(
        {
          run_id: "run_prev",
          run_status: "validating",
          result_state: null,
          cancel_requested: false,
        },
        { status: 201 },
      ),
    )
    .mockResolvedValueOnce(jsonResponse(completedSnapshot))
    .mockResolvedValueOnce(jsonResponse(completedResult))
    .mockImplementationOnce(() =>
      delayedJsonResponse(
        {
          error: {
            code: "ENDPOINT_UNREACHABLE",
            message: "endpoint request failed",
          },
        },
        1100,
        { status: 400 },
      ),
    )
    .mockImplementationOnce(() => delayedJsonResponse(completedSnapshot, 700))
    .mockResolvedValueOnce(jsonResponse(completedResult))

  vi.stubGlobal("fetch", fetchMock)
  renderConsole()
  await flushAsyncWork()

  fillAndSubmitForm()
  await flushAsyncWork()
  expect(screen.getByText("✅ Formal Conclusion · Highly Consistent")).toBeInTheDocument()

  fireEvent.change(screen.getByLabelText("Base URL"), {
    target: { value: "https://invalid.example.com/v1" },
  })
  fireEvent.click(screen.getByRole("button", { name: "Start Check" }))
  await flushAsyncWork()

  await advancePolling(1100)
  expect(screen.getByText("Configuration Error")).toBeInTheDocument()
  expect(
    screen.getByText(
      "The configured endpoint could not be reached. Check the Base URL, DNS resolution, and network connectivity.",
    ),
  ).toBeInTheDocument()

  await advancePolling(1000)
  expect(
    screen.getByText(
      "The configured endpoint could not be reached. Check the Base URL, DNS resolution, and network connectivity.",
    ),
  ).toBeInTheDocument()
  expect(screen.queryByText("✅ Formal Conclusion · Highly Consistent")).not.toBeInTheDocument()
})
