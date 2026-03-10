# Online Detection Web API Design

**Date**

2026-03-10

**Status**

Approved for planning

**Problem**

The repository already has a file-based Python engine, stable Pydantic contracts, and a CLI for probing, suite execution, and comparison. The new web console needs a real backend, but the repository does not yet define an HTTP contract for starting a live run, polling progress, or fetching a terminal result.

Without a dedicated API contract:

- frontend and backend will drift on state naming
- CLI and web semantics will fork
- abnormal cases such as `provisional`, `insufficient_evidence`, and `incompatible_protocol` will be handled inconsistently
- localized UI copy will be forced to depend on backend prose instead of machine-readable state

**Goal**

Define a versioned HTTP contract for the online detection workflow that:

- serves the web MVP and only the web MVP
- stays aligned with existing CLI and engine contracts
- exposes polling-friendly resources for a five-prompt live run
- makes result-state rules explicit
- keeps localization responsibility in the frontend

**Constraints**

- scope is limited to online detection workflow
- training, calibration, and profile construction stay out of scope
- API payloads should align with current Python contracts and JSON schemas where practical
- `api_key` must be accepted only for run creation and never returned
- the API must support the web UI states already approved:
  - validating
  - running
  - formal result
  - provisional
  - insufficient evidence
  - incompatible protocol
  - configuration error
  - stopped

## Approaches Considered

1. Expose raw CLI artifacts directly over HTTP.
   This is fast, but it leaks too much engine structure into the browser and makes frontend evolution brittle.
2. Build a thin orchestration API over existing contracts.
   This keeps semantics aligned with the engine while still giving the browser a stable, workflow-oriented surface.
3. Design a frontend-first API with unrelated DTOs.
   This is flexible for the web app, but it would fork meaning from CLI and file artifacts.

**Recommendation**

Use approach 2.

## Design

### 1. Contract layering

The design should preserve a clear separation:

1. engine contracts remain the source of truth for artifact semantics
2. CLI remains an operator interface over the engine
3. Web API becomes a thin workflow-oriented projection for the browser

This means the Web API should reuse existing state meaning, but not mirror internal file artifacts field-for-field.

### 2. Resources

The HTTP surface should expose only three resources:

- `fingerprint_model`
- `run`
- `run_result`

This is enough for the single-page web MVP and avoids prematurely exposing operator-oriented engine features.

### 3. Polling model

The browser should not orchestrate prompt execution. It should:

1. create one run
2. receive one `run_id`
3. poll run state
4. fetch terminal result when the run settles

This keeps the browser thin and makes the backend the owner of prompt progress, cancellation, and result determination.

### 4. State model

The design explicitly separates:

- lifecycle state: `run_status`
- interpretation state: `result_state`

This prevents confusing combinations such as a still-running run being treated as provisional or final.

### 5. Localization boundary

The API should return machine-readable codes, not final UI phrasing.

Examples:

- `summary_code`
- `error.code`
- `result_state`

The frontend owns localized labels, descriptions, and operator guidance.

### 6. Evidence rules

The completion rules from the approved UI design become contract rules:

- `5/5` usable prompts -> `formal_result`
- `3/5` or `4/5` usable prompts -> `provisional`
- `<3/5` usable prompts -> `insufficient_evidence`
- protocol incompatibility overrides evidence-count rules

For the shipped web MVP, the five-prompt run is backed by `fingerprint-suite-v3`.

These rules must live in the contract and not only in the web UI.

### 7. Cancellation semantics

Cancellation should be cooperative and asynchronous.

The cancel endpoint should acknowledge the request with `202 Accepted` and set `cancel_requested=true`. The frontend then continues polling until the run reaches `stopped`.

This avoids incorrectly promising that the in-flight upstream request stopped synchronously.

## Outcome

The approved direction is:

- versioned HTTP contract under `/api/v1`
- online-detection-only scope
- thin orchestration API over existing engine and CLI semantics
- polling-based run model
- machine-readable payloads with frontend-owned localization
- explicit lifecycle/result-state separation
- explicit evidence sufficiency rules

The source-of-truth contract lives in:

- `docs/apis/web_api_contract.md`
