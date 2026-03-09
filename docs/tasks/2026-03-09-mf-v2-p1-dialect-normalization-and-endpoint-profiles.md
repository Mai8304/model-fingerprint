# V2 P1 Dialect Normalization and Endpoint Profiles Implementation Plan

**Goal:** Introduce the live transport stack that is organized by protocol dialect and endpoint capability profile, not by provider brand.

**Architecture:** One dialect adapter turns a normalized request into a wire request and parses a wire response into a normalized completion. Endpoint profiles provide declarative field mappings, capability flags, and timeout/retry policy.

**Tech Stack:** Python 3.12+, urllib/httpx-style HTTP client, pytest, PyYAML, Pydantic v2

**Status:** Completed on 2026-03-09

**Acceptance Evidence:**
- `uv run pytest tests/transports tests/e2e/test_suite_runner.py -q`
- `uv run ruff check src tests`
- `uv run mypy src`

---

### Task 1: Add normalized request/completion models and dialect adapter interfaces

**Files:**
- Create: `src/modelfingerprint/dialects/base.py`
- Create: `src/modelfingerprint/dialects/openai_chat.py`
- Modify: `src/modelfingerprint/adapters/openai_chat.py`
- Create: `tests/transports/test_openai_chat_dialect.py`

**Step 1: Write failing dialect tests**

Test intent:
- build one wire request from a normalized prompt definition
- map `max_output_tokens` to the dialect-specific request field without changing its value
- parse answer text, reasoning text, finish reason, and usage from a dialect response
- reject impossible field-path mappings with explicit errors

Run: `uv run pytest tests/transports/test_openai_chat_dialect.py -q`
Expected: FAIL because the current adapter boundary is only a placeholder

**Step 2: Implement the dialect interfaces**

Implementation intent:
- keep the code path centered on semantic fields, not provider names
- make field-path overrides come from endpoint profiles
- keep reasoning extraction separate from final answer extraction

**Step 3: Re-run the dialect tests**

Run: `uv run pytest tests/transports/test_openai_chat_dialect.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/dialects src/modelfingerprint/adapters/openai_chat.py tests/transports/test_openai_chat_dialect.py
git commit -m "feat: add dialect adapters and normalized completion parsing"
```

### Task 2: Implement endpoint-profile loading and capability validation

**Files:**
- Create: `src/modelfingerprint/services/endpoint_profiles.py`
- Create: `tests/transports/test_endpoint_profile_loader.py`
- Create: `tests/fixtures/endpoint_profiles/*.yaml`

**Step 1: Write failing endpoint-profile loader tests**

Test intent:
- load endpoint profiles from disk
- validate required capability flags before any live request is sent
- reject missing reasoning paths when a profile claims visible reasoning support

Run: `uv run pytest tests/transports/test_endpoint_profile_loader.py -q`
Expected: FAIL because endpoint-profile loading does not exist yet

**Step 2: Implement the loader and validator**

Implementation intent:
- keep secrets outside committed profile YAML
- allow one dialect to back many endpoints
- make capability mismatch a typed error instead of a best-effort warning

**Step 3: Re-run the tests**

Run: `uv run pytest tests/transports/test_endpoint_profile_loader.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/endpoint_profiles.py tests/transports/test_endpoint_profile_loader.py tests/fixtures/endpoint_profiles
git commit -m "feat: add endpoint profile loading and capability validation"
```

### Task 3: Replace the live HTTP transport with fixed-protocol execution, retries, and traces

**Files:**
- Create: `src/modelfingerprint/transports/http_client.py`
- Create: `src/modelfingerprint/transports/live_runner.py`
- Modify: `src/modelfingerprint/services/suite_runner.py`
- Create: `tests/transports/test_live_runner.py`

**Step 1: Write failing live-runner tests**

Test intent:
- execute prompts sequentially under a fixed immutable request spec
- persist prompt-level request/response traces
- retry only retryable transport failures
- never mutate prompt content or output-token cap across retries

Run: `uv run pytest tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py -q`
Expected: FAIL because the current suite runner assumes a trivial completion interface

**Step 2: Implement the fixed-protocol live runner**

Implementation intent:
- run with per-prompt checkpointing
- preserve all prompt execution statuses
- treat unsupported capability and truncation as typed outcomes
- keep concurrency at one by default to avoid false operational variance during fingerprint collection

**Step 3: Re-run the suite-runner tests**

Run: `uv run pytest tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/transports src/modelfingerprint/services/suite_runner.py tests/transports/test_live_runner.py tests/e2e/test_suite_runner.py
git commit -m "feat: add fixed-protocol live runner with traces and retries"
```

### Task 4: Add no-adaptation protocol invariants

**Files:**
- Create: `tests/transports/test_protocol_invariants.py`
- Modify: `src/modelfingerprint/services/suite_runner.py`
- Modify: `src/modelfingerprint/dialects/openai_chat.py`

**Step 1: Write failing invariant tests**

Test intent:
- if the prompt requires JSON mode and the endpoint profile does not support it, the prompt is marked `unsupported_capability`
- if the endpoint profile maps output-token cap to a different field name, the numeric cap is preserved exactly
- no code path lowers `max_output_tokens` or rewrites prompt messages dynamically

Run: `uv run pytest tests/transports/test_protocol_invariants.py -q`
Expected: FAIL because these invariants are not yet enforced centrally

**Step 2: Implement invariant enforcement**

Implementation intent:
- capability mismatch is not “adapted away”
- semantic request values are immutable
- protocol incompatibility is preserved as evidence

**Step 3: Re-run the invariant tests**

Run: `uv run pytest tests/transports/test_protocol_invariants.py -q`
Expected: PASS

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/suite_runner.py src/modelfingerprint/dialects/openai_chat.py tests/transports/test_protocol_invariants.py
git commit -m "feat: enforce fixed protocol invariants for live runs"
```

### Phase exit criteria

P1 is complete only when:

1. one dialect adapter is fully tested end-to-end
2. endpoint profiles load from YAML and validate capabilities
3. live runs preserve traces and prompt-level statuses
4. no code path silently lowers output-token caps or rewrites prompts
