# Model Fingerprint Diagnostics Workbench Design

**Date**

2026-03-11

**Status**

Approved for planning

**Problem**

The current web console is usable as a thin wrapper around the online fingerprint engine, but it is not usable as a debugging surface for advanced users.

The main failures are structural:

- in-flight runs expose only coarse status, so the UI often jumps from `0 / 5` to `5 / 5`
- the result area compresses rich backend diagnostics into a short summary card
- `insufficient_evidence` is presented as a generic warning instead of a blocking report
- remote configuration failures such as invalid API keys, unreachable endpoints, or unknown models are not mapped to field-level UI feedback

The backend already computes materially richer information than the current frontend shows. The missing piece is a diagnostics-oriented web contract and UI layout.

**Goal**

Design a diagnostics-first workbench for advanced users that:

- shows real prompt-by-prompt progress during an active run
- exposes technical transport and parsing details without hiding them behind generic copy
- renders a structured formal verdict when enough evidence exists
- renders a structured blocking report when evidence is insufficient
- maps configuration and provider failures to both field-level and run-level UI

**Non-Goals**

- no redesign of the left-side configuration form beyond error handling improvements
- no login, persistence, or multi-run history in this phase
- no WebSocket or SSE transport in this phase; polling remains acceptable if backend snapshots become sufficiently rich
- no change to the fingerprint algorithm itself

**Constraints**

- the web flow must continue to use the existing `fingerprint-suite-v3`
- API keys and authorization headers must remain masked in every UI surface
- the diagnostics UI is for advanced users, so HTTP status, provider messages, error codes, timings, and coverage values may be shown by default
- the implementation should minimize drift from the CLI and backend result semantics

## Approaches Considered

1. Expand the existing result card with more paragraphs and badges.

This is the smallest UI change, but it does not fix the core issue. The current shape is still a single summary card, so prompt-level reasoning and error triage remain hidden.

2. Replace the result card with a diagnostics workbench while keeping the current page shell.

This introduces a staged overview, prompt diagnostics table, and structured report without rewriting the entire page. It keeps the stable left-column configuration panel and replaces the right-column summary with a research-tool-style workbench.

3. Build a fully split NOC-style interface with a permanent side log and deep drill-down panels.

This maximizes observability, but it is larger than the immediate need and would introduce more UI and interaction complexity before the data contract is stabilized.

**Recommendation**

Use approach 2.

It fixes the actual observability and diagnosis problems while preserving the current shell and minimizing unnecessary UI churn.

## Design

### 1. Page Shape

Keep the existing two-column page:

- left: configuration panel
- right: diagnostics workbench

The right column should no longer be a single result card. It should become a stable top-to-bottom workbench with four sections:

1. run overview
2. stage timeline
3. prompt diagnostics table
4. conclusion and report

### 2. Run Overview

The top card should show immutable run identity and current execution status:

- `base_url`
- `model_name`
- selected fingerprint model
- `run_id`
- `suite_id`
- `created_at`
- `updated_at`
- current stage badge
- current prompt badge if one is active

This card answers the operator question: "What exactly am I looking at right now?"

### 3. Stage Timeline

The next card should show lifecycle stages explicitly:

- `Config Validation`
- `Endpoint Resolution`
- `Capability Probe`
- `Prompt Execution`
- `Comparison`

Each stage should expose:

- state: `pending`, `running`, `completed`, `failed`
- start and finish timestamps when available
- one short technical message

This solves the "0 / 5 to 5 / 5" problem only if the backend writes stage transitions and prompt updates during execution.

### 4. Prompt Diagnostics Table

The prompt area is the core of the diagnostics workbench.

Default rows:

- one row per prompt in `fingerprint-suite-v3`
- rows always visible, even before execution starts

Default columns:

- `prompt_id`
- `status`
- `elapsed_ms`
- `first_byte_ms`
- `http_status`
- `error_code`
- `finish_reason`
- `bytes_received`
- `parse_status`
- `scoreable`

Expandable details per row:

- `error_detail`
- provider message
- transport phase
- timeout policy in effect
- whether answer text was present
- whether reasoning text was present
- whether the prompt contributed scoreable evidence

This section makes prompt-level failures diagnosable without reading trace files on disk.

### 5. Formal Conclusion

When enough evidence exists, the conclusion section should show a structured result instead of a short paragraph.

Required fields:

- verdict
- claimed model similarity
- top candidate model
- top candidate similarity
- margin
- protocol status
- answer coverage
- reasoning coverage
- capability similarity
- content similarity
- hard mismatches
- protocol issues

The verdict sentence should stay brief, but the supporting evidence must remain directly visible below it.

### 6. Insufficient Evidence Report

`insufficient_evidence` must have its own report template instead of reusing the verdict card.

Required sections:

- overall reason
- blocking reasons
- failed prompt list
- coverage gaps
- protocol issues
- recommended next actions

Example structure:

- `scoreable prompts: 2 / 5`
- `answer coverage: 0.40`
- `reasoning coverage: 0.20`
- `blocking reasons: RESPONSE_TIMEOUT on p022, UNPARSEABLE_RESPONSE on p024`

This tells the operator why the system cannot conclude, rather than merely stating that it cannot.

### 7. Configuration and Provider Error Handling

Remote errors must be shown at three levels:

1. field-level inline error
2. run-level error summary
3. technical details panel

Expected mappings:

- `AUTH_FAILED` -> `apiKey`
- `MODEL_NOT_FOUND` -> `modelName`
- `INVALID_BASE_URL` and `ENDPOINT_UNREACHABLE` -> `baseUrl`
- `RATE_LIMITED`, `PROVIDER_SERVER_ERROR`, `UNSUPPORTED_ENDPOINT_PROTOCOL` -> run-level summary plus technical detail

The top summary should explain the failed stage and primary cause. The technical detail panel should expose provider message, internal error code, HTTP status, and retryability.

### 8. Data Contract Changes

The current snapshot contract is too thin for a diagnostics UI.

`WebRunSnapshot` should be extended to include:

- `stage`
- `stage_message`
- `stage_started_at`
- `stage_finished_at`
- `current_prompt_index`
- prompt-level metrics:
  - `started_at`
  - `finished_at`
  - `elapsed_ms`
  - `first_byte_ms`
  - `bytes_received`
  - `finish_reason`
  - `parse_status`
  - `answer_present`
  - `reasoning_present`
  - `scoreable`

The final report should expose structured comparison diagnostics that the frontend can render directly instead of reverse-engineering from summary strings.

### 9. Backend Execution Model

The UI cannot show real progress until the backend persists intermediate state.

That requires:

- stage transition writes
- prompt `running` writes before each prompt starts
- prompt completion or failure writes immediately after each prompt resolves
- result/report write only after comparison completes

Polling every second is acceptable for this phase if each poll returns updated stage and prompt state.

### 10. Testing Strategy

Testing should cover:

- backend snapshot projection for every stage
- backend report payload for `formal_result`, `insufficient_evidence`, and `configuration_error`
- frontend render tests for:
  - running timeline progression
  - prompt diagnostics rows
  - formal result report
  - insufficient evidence report
  - field-level remote error mapping
- one Playwright path each for:
  - successful completion
  - insufficient evidence
  - invalid API key

## Acceptance Criteria

- active runs show stage progression and prompt-by-prompt movement
- prompt rows update during execution, not only at the end
- formal results show structured evidence, not only a short summary
- insufficient-evidence runs show blocking reasons and next actions
- invalid `apiKey`, `baseUrl`, and `modelName` surface actionable UI feedback at the right level
- no secret values are rendered in the UI
