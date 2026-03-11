import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, vi } from "vitest"

import { DetectionConsole } from "@/components/detection-console"
import { Providers } from "@/components/providers"

function jsonResponse(payload: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(payload), {
    headers: {
      "content-type": "application/json",
    },
    ...init,
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

test("loads registry, submits a run, polls progress, and renders provisional output", async () => {
  const fetchMock = vi.fn()
  fetchMock
    .mockResolvedValueOnce(
      jsonResponse({
        items: [
          { id: "deepseek-chat", label: "DeepSeek Chat", suite_id: "fingerprint-suite-v3", available: true },
          { id: "glm-5", label: "GLM-5", suite_id: "fingerprint-suite-v3", available: true },
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
        progress: {
          completed_prompts: 2,
          failed_prompts: 0,
          total_prompts: 5,
          current_prompt_id: "p023",
          eta_seconds: 45,
        },
        prompts: [],
        failure: null,
      }),
    )
    .mockResolvedValueOnce(
      jsonResponse({
        run_id: "run_123",
        run_status: "completed",
        result_state: "provisional",
        cancel_requested: false,
        created_at: "2026-03-10T15:30:00Z",
        updated_at: "2026-03-10T15:30:30Z",
        input: {
          base_url: "https://api.example.com/v1",
          model_name: "gpt-4o-mini",
          fingerprint_model_id: "glm-5",
        },
        progress: {
          completed_prompts: 4,
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
        run_id: "run_123",
        result_state: "provisional",
        selected_fingerprint: {
          id: "glm-5",
          label: "GLM-5",
        },
        completed_prompts: 4,
        total_prompts: 5,
        verdict: "match",
        summary: {
          similarity_score: 0.94,
          confidence_low: null,
          confidence_high: null,
          top_candidate_model_id: "glm-5",
          top_candidate_label: "GLM-5",
        },
        candidates: [
          {
            model_id: "glm-5",
            label: "GLM-5",
            similarity: 0.94,
          },
        ],
        diagnostics: {
          protocol_status: "compatible",
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

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/runs",
    expect.objectContaining({
      method: "POST",
    }),
  )

  await advancePolling(1000)
  expect(screen.getAllByText("2 / 5").length).toBeGreaterThan(0)
  expect(screen.getByText("Prompt 3")).toBeInTheDocument()
  expect(screen.getByText("Running Diagnostics")).toBeInTheDocument()

  await advancePolling(1000)
  expect(screen.getByText("Detailed Result")).toBeInTheDocument()
  expect(screen.getByText(/Verdict: match/i)).toBeInTheDocument()
  expect(screen.getByText("Top Candidates")).toBeInTheDocument()
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
  expect(screen.getByText("Insufficient Evidence")).toBeInTheDocument()
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
