# Web API Contract

**Status**

Approved for implementation

**Version**

`v1`

**Path Prefix**

`/api/v1`

## 1. Scope

This contract defines the HTTP API for the online detection workflow only.

Included:

- list available fingerprint models
- start one live detection run
- poll run progress
- fetch terminal result
- cancel one in-flight run

Excluded:

- profile building
- calibration
- training pipelines
- historical run dashboards
- batch execution

## 2. Design Principles

### 2.1 Contract layering

The repository has three relevant layers:

1. engine contracts
   - `src/modelfingerprint/contracts/run.py`
   - `src/modelfingerprint/contracts/comparison.py`
2. CLI orchestration
   - `src/modelfingerprint/cli.py`
3. Web API contract
   - this document

The Web API is a thin orchestration layer over the existing engine and CLI semantics. It must not invent a separate verdict model.

### 2.2 Payload naming

All HTTP payload keys use `snake_case`.

Reason:

- existing Python contracts and JSON schemas already use `snake_case`
- this keeps Web API payloads aligned with file artifacts and CLI JSON output
- frontend adapters may map to `camelCase` internally if needed

### 2.3 Machine-readable first

The API returns machine-readable states and codes. Frontend copy is localized in the web app.

The API should prefer:

- `code`
- `status`
- `result_state`
- `summary_code`

and avoid embedding user-facing English prose as the primary contract.

### 2.4 Security boundary

- `api_key` is accepted only in `POST /api/v1/runs`
- `api_key` must never appear in any response payload
- `api_key` is for the current run only and must not be persisted as product data

## 3. Resources

### 3.1 `fingerprint_model`

```json
{
  "id": "claude-3.7-sonnet",
  "label": "Claude 3.7 Sonnet",
  "suite_id": "fingerprint-suite-v3",
  "available": true
}
```

Fields:

- `id`: stable fingerprint identifier
- `label`: display label
- `suite_id`: backing prompt suite identifier
- `available`: whether the model is currently selectable

### 3.2 `run`

```json
{
  "run_id": "run_20260310_143000_8f2b",
  "run_status": "running",
  "result_state": null,
  "cancel_requested": false,
  "created_at": "2026-03-10T14:30:00+08:00",
  "updated_at": "2026-03-10T14:33:12+08:00",
  "input": {
    "base_url": "https://api.example.com/v1",
    "model_name": "gpt-4o-mini",
    "fingerprint_model_id": "claude-3.7-sonnet"
  },
  "progress": {
    "completed_prompts": 2,
    "failed_prompts": 1,
    "total_prompts": 5,
    "current_prompt_id": "p003",
    "eta_seconds": 360
  },
  "prompts": [
    {
      "prompt_id": "p001",
      "status": "completed",
      "elapsed_seconds": 56,
      "summary_code": "STRUCTURE_PARSED",
      "error_code": null,
      "error_detail": null,
      "http_status": null
    }
  ],
  "failure": null
}
```

Notes:

- `input` must never include `api_key`
- prompt display names are owned by the frontend via prompt id mapping
- `error_detail` is optional diagnostic detail and not a localization source

### 3.3 `run_result`

```json
{
  "run_id": "run_20260310_143000_8f2b",
  "result_state": "formal_result",
  "selected_fingerprint": {
    "id": "claude-3.7-sonnet",
    "label": "Claude 3.7 Sonnet"
  },
  "completed_prompts": 5,
  "total_prompts": 5,
  "verdict": "mismatch",
  "summary": {
    "similarity_score": 0.824,
    "confidence_low": 0.781,
    "confidence_high": 0.869,
    "top_candidate_model_id": "gpt-4.1-mini",
    "top_candidate_label": "GPT-4.1 Mini"
  },
  "candidates": [
    {
      "model_id": "gpt-4.1-mini",
      "label": "GPT-4.1 Mini",
      "similarity": 0.912
    },
    {
      "model_id": "claude-3.7-sonnet",
      "label": "Claude 3.7 Sonnet",
      "similarity": 0.824
    }
  ],
  "diagnostics": {
    "protocol_status": "compatible",
    "protocol_issues": [],
    "hard_mismatches": []
  }
}
```

Notes:

- `candidates` is omitted or empty when the result state does not allow ranking output
- `similarity_score` and confidence interval are only present for `formal_result`

## 4. State Model

### 4.1 `run_status`

Lifecycle state for the run resource.

Allowed values:

- `validating`
- `running`
- `completed`
- `configuration_error`
- `stopped`

### 4.2 `result_state`

Interpretation state for the finished run.

Allowed values:

- `formal_result`
- `provisional`
- `insufficient_evidence`
- `incompatible_protocol`
- `configuration_error`
- `stopped`

### 4.3 State rules

Allowed combinations:

- `run_status=validating`, `result_state=null`
- `run_status=running`, `result_state=null`
- `run_status=completed`, `result_state=formal_result`
- `run_status=completed`, `result_state=provisional`
- `run_status=completed`, `result_state=insufficient_evidence`
- `run_status=completed`, `result_state=incompatible_protocol`
- `run_status=configuration_error`, `result_state=configuration_error`
- `run_status=stopped`, `result_state=stopped`

Disallowed combinations:

- `run_status=running`, `result_state=formal_result`
- `run_status=running`, `result_state=provisional`
- `run_status=completed`, `result_state=null`

### 4.4 Completion rules

- if all `5/5` prompts complete and protocol is compatible:
  - `result_state=formal_result`
- if `3/5` or `4/5` prompts are usable and protocol is compatible:
  - `result_state=provisional`
- if fewer than `3/5` prompts are usable:
  - `result_state=insufficient_evidence`
- if protocol compatibility fails:
  - `result_state=incompatible_protocol`
  - this takes precedence over provisional or insufficient evidence

## 5. Prompt Progress Model

### 5.1 Prompt item

Each prompt entry in `run.prompts` uses:

- `prompt_id`
- `status`
- `elapsed_seconds`
- `summary_code`
- `error_code`
- `error_detail`
- `http_status`

### 5.2 Prompt status values

Frontend-facing prompt statuses:

- `pending`
- `running`
- `completed`
- `failed`
- `stopped`

These statuses are derived from lower-level engine outcomes such as:

- `timeout`
- `transport_error`
- `unsupported_capability`
- `truncated`
- `invalid_response`
- `canonicalization_error`

### 5.3 Prompt summary codes

Initial MVP summary codes:

- `WAITING_FOR_RESPONSE`
- `STRUCTURE_PARSED`
- `FEATURES_EXTRACTED`
- `PROTOCOL_CHECKED`
- `CANDIDATE_SCORED`
- `RETRYING`

The frontend owns localized phrasing for these codes.

## 6. Error Model

### 6.1 Error object

```json
{
  "code": "AUTH_FAILED",
  "message": "upstream endpoint returned 401",
  "retryable": false,
  "http_status": 401
}
```

Fields:

- `code`: stable machine-readable error code
- `message`: optional raw operator/debug detail
- `retryable`: whether retry is reasonable
- `http_status`: upstream HTTP status when available

### 6.2 Error code families

Startup and configuration:

- `INVALID_REQUEST`
- `UNKNOWN_FINGERPRINT_MODEL`
- `AUTH_FAILED`
- `ENDPOINT_UNREACHABLE`
- `MODEL_NOT_FOUND`
- `UNSUPPORTED_ENDPOINT_PROTOCOL`

Runtime prompt failures:

- `RESPONSE_TIMEOUT`
- `TRANSPORT_ERROR`
- `UNPARSEABLE_RESPONSE`
- `CANONICALIZATION_ERROR`
- `UNSUPPORTED_CAPABILITY`
- `TRUNCATED_RESPONSE`

Terminal run conditions:

- `INSUFFICIENT_EVIDENCE`
- `INCOMPATIBLE_PROTOCOL`
- `RUN_STOPPED`
- `RUN_NOT_FOUND`
- `RUN_NOT_COMPLETED`

## 7. Endpoints

### 7.1 `GET /api/v1/fingerprints`

Returns the selectable fingerprint models for the current web console.

Response `200`:

```json
{
  "items": [
    {
      "id": "claude-3.7-sonnet",
      "label": "Claude 3.7 Sonnet",
      "suite_id": "fingerprint-suite-v3",
      "available": true
    }
  ]
}
```

### 7.2 `POST /api/v1/runs`

Creates and starts a new live detection run.

Request:

```json
{
  "api_key": "sk-xxxxx",
  "base_url": "https://api.example.com/v1",
  "model_name": "gpt-4o-mini",
  "fingerprint_model_id": "claude-3.7-sonnet"
}
```

Response `201`:

```json
{
  "run_id": "run_20260310_143000_8f2b",
  "run_status": "validating",
  "result_state": null,
  "cancel_requested": false
}
```

Rules:

- request validation errors return `400`
- unknown fingerprint id returns `404`
- upstream credential or endpoint failures are represented as run state transitions, not HTTP create-time failures

### 7.3 `GET /api/v1/runs/{run_id}`

Returns the current run snapshot for polling.

Response `200`:

```json
{
  "run_id": "run_20260310_143000_8f2b",
  "run_status": "running",
  "result_state": null,
  "cancel_requested": false,
  "created_at": "2026-03-10T14:30:00+08:00",
  "updated_at": "2026-03-10T14:33:12+08:00",
  "input": {
    "base_url": "https://api.example.com/v1",
    "model_name": "gpt-4o-mini",
    "fingerprint_model_id": "claude-3.7-sonnet"
  },
  "progress": {
    "completed_prompts": 2,
    "failed_prompts": 1,
    "total_prompts": 5,
    "current_prompt_id": "p003",
    "eta_seconds": 360
  },
  "prompts": [],
  "failure": null
}
```

Response `404`:

```json
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "run_id does not exist"
  }
}
```

### 7.4 `GET /api/v1/runs/{run_id}/result`

Returns the terminal result projection for a completed, stopped, or failed run.

Response `200`:

- `formal_result`
- `provisional`
- `insufficient_evidence`
- `incompatible_protocol`
- `configuration_error`
- `stopped`

Response `409` while the run is still active:

```json
{
  "error": {
    "code": "RUN_NOT_COMPLETED",
    "message": "run is still in progress"
  }
}
```

### 7.5 `POST /api/v1/runs/{run_id}/cancel`

Requests cooperative cancellation for an in-flight run.

Response `202`:

```json
{
  "run_id": "run_20260310_143000_8f2b",
  "run_status": "running",
  "result_state": null,
  "cancel_requested": true
}
```

Rules:

- cancellation is cooperative
- `202` means the stop request was accepted, not that the run has already reached `stopped`
- the frontend should continue polling `GET /api/v1/runs/{run_id}` until the run reaches terminal state

## 8. CLI and Engine Mapping

### 8.1 Endpoint mapping

- `GET /api/v1/fingerprints`
  - backed by the prebuilt fingerprint registry derived from stored profiles
- `POST /api/v1/runs`
  - starts capability probing and suite execution
  - aligned with:
    - `probe-capabilities`
    - `run-suite`
- `GET /api/v1/runs/{run_id}`
  - projects live execution into a polling snapshot
  - aligned with:
    - `RunArtifact`
    - runtime progress state
- `GET /api/v1/runs/{run_id}/result`
  - projects terminal comparison output
  - aligned with:
    - `compare`
    - `ComparisonArtifact`
    - verdict decision logic
- `POST /api/v1/runs/{run_id}/cancel`
  - aligned with cooperative runtime cancellation described in the runtime design docs

### 8.2 Artifact alignment

The HTTP API should map from engine artifacts rather than fork their meaning:

- `RunArtifact.prompt_count_total` -> `run.progress.total_prompts`
- `RunArtifact.prompt_count_completed` -> `run.progress.completed_prompts`
- `RunArtifact.protocol_compatibility.satisfied` -> `result_state` precedence
- `ComparisonArtifact.summary.verdict` -> `run_result.verdict`
- `ComparisonArtifact.candidates` -> `run_result.candidates`

## 9. Non-Goals

- no SSE or WebSocket in `v1`
- no run history in `v1`
- no artifact download endpoint in `v1`
- no training, calibration, or profile build endpoints in `v1`
- no guarantee that the frontend can reconstruct an in-flight run without polling this API
