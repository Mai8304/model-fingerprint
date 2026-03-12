# Multi-Protocol Transport Architecture Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the custom live transport with an `httpx`-based transport, formalize protocol-family adapters, introduce profile-driven quirk handling, and redesign runtime policy around task intent so broad provider compatibility improves without creating one adapter per provider.

**Architecture:** Keep the live execution pipeline layered. First stabilize the transport boundary with a single `httpx` implementation, then make adapter selection depend on `protocol_family`, then move provider/model exceptions into endpoint-profile quirks, and finally redesign runtime policy to emit attempt tiers based on task intent. Each phase should preserve a shippable live path and use targeted regression tests before the next phase begins.

**Tech Stack:** Python, Pydantic, Typer, pytest, uv, httpx, SSE parsing helpers

---

### Task 1: Introduce an `httpx` transport seam without changing callers

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/http_client.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_http_client.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_live_runner.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_http_client.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_live_runner.py`

**Step 1: Write the failing transport regression tests**

Add tests that prove:

- blocking JSON responses complete without custom socket polling
- SSE responses still parse into the existing normalized payload shape
- connect, first-byte, idle, and total-deadline failures map to stable transport error kinds

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/transports/test_http_client.py tests/transports/test_live_runner.py -q
```

Expected: FAIL because the current transport does not expose the new timeout dimensions and still depends on the legacy client behavior.

**Step 3: Write minimal implementation**

Refactor `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/http_client.py` to:

- create a single `httpx`-backed transport implementation
- preserve the current public send/start abstraction expected by `LiveRunner`
- keep response decoding and SSE normalization isolated from protocol semantics

Adjust `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py` only as needed to consume the new transport timeout model.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/transports/test_http_client.py tests/transports/test_live_runner.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/transports/http_client.py \
  src/modelfingerprint/transports/live_runner.py \
  tests/transports/test_http_client.py \
  tests/transports/test_live_runner.py
git commit -m "refactor: move live transport to httpx"
```

### Task 2: Add protocol-family routing to endpoint profiles

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/contracts/endpoint.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/endpoint_profiles.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/cli.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/webapi/run_orchestrator.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/contracts/test_endpoint_profiles.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/test_cli_commands.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/contracts/test_endpoint_profiles.py`

**Step 1: Write the failing schema and loader tests**

Add assertions that endpoint profiles now carry:

- `protocol_family`
- optional `provider_id`
- optional `quirks`
- optional `runtime_profile_id`

Ensure the loader rejects unknown protocol families.

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/contracts/test_endpoint_profiles.py -q
```

Expected: FAIL because the current schema does not define those fields.

**Step 3: Write minimal implementation**

Update `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/contracts/endpoint.py` and `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/endpoint_profiles.py` so profiles can declare protocol-family metadata while preserving current file compatibility for existing OpenAI-compatible profiles.

Update CLI and web endpoint resolution to read the new fields without changing public input shape.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/contracts/test_endpoint_profiles.py tests/test_cli_commands.py tests/webapi/test_run_orchestrator.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/contracts/endpoint.py \
  src/modelfingerprint/services/endpoint_profiles.py \
  src/modelfingerprint/cli.py \
  src/modelfingerprint/webapi/run_orchestrator.py \
  tests/contracts/test_endpoint_profiles.py \
  tests/test_cli_commands.py \
  tests/webapi/test_run_orchestrator.py
git commit -m "feat: add protocol-family metadata to endpoint profiles"
```

### Task 3: Rename and stabilize the OpenAI-compatible adapter boundary

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/dialects/base.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/dialects/openai_chat.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_openai_chat_dialect.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_openai_chat_dialect.py`

**Step 1: Write the failing adapter selection tests**

Add tests that prove:

- adapter selection depends on `protocol_family`, not provider name
- OpenAI-compatible profiles still build and parse the same normalized shapes
- current Moonshot/OpenRouter/OpenAI-compatible cases stay on the standard adapter path

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/transports/test_openai_chat_dialect.py -q
```

Expected: FAIL because the current adapter boundary is still named and selected as a single `openai_chat` dialect.

**Step 3: Write minimal implementation**

Refactor the dialect layer so the adapter concept is explicitly protocol-family-based while preserving current behavior for existing OpenAI-compatible profiles.

Do not introduce Anthropic or Gemini adapters in this task; only make room for them.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/transports/test_openai_chat_dialect.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/dialects/base.py \
  src/modelfingerprint/dialects/openai_chat.py \
  src/modelfingerprint/transports/live_runner.py \
  tests/transports/test_openai_chat_dialect.py
git commit -m "refactor: treat adapters as protocol families"
```

### Task 4: Introduce a quirk registry for provider and model exceptions

**Files:**
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/dialects/quirks.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/contracts/endpoint.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/dialects/openai_chat.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/capability_probe.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/endpoint-profiles/moonshot-kimi-k2.5.yaml`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_openai_chat_dialect.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_capability_probe.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_capability_probe.py`

**Step 1: Write the failing quirk tests**

Add tests that prove:

- unsupported sampling parameters are removed through quirk application rather than hard-coded provider checks
- Moonshot tool probe retries through a quirk-driven request mutation
- vision probe fallback to data URL is driven by an explicit quirk path

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/transports/test_openai_chat_dialect.py tests/services/test_capability_probe.py -q
```

Expected: FAIL because quirks are not yet modeled as first-class rules.

**Step 3: Write minimal implementation**

Create a small quirk registry that supports:

- request-time mutation
- response normalization
- probe-only failure handling

Wire quirk application into the OpenAI-compatible adapter and capability probe path.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/transports/test_openai_chat_dialect.py tests/services/test_capability_probe.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/dialects/quirks.py \
  src/modelfingerprint/contracts/endpoint.py \
  src/modelfingerprint/dialects/openai_chat.py \
  src/modelfingerprint/services/capability_probe.py \
  endpoint-profiles/moonshot-kimi-k2.5.yaml \
  tests/transports/test_openai_chat_dialect.py \
  tests/services/test_capability_probe.py
git commit -m "feat: add profile-driven protocol quirks"
```

### Task 5: Redesign runtime policy around task intent and tiered attempts

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/runtime_policy.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/contracts/run.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_runtime_policy.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_live_runner.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/test_cli_commands.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_runtime_policy.py`

**Step 1: Write the failing runtime policy tests**

Add tests for:

- `structured_extraction`, `capability_probe`, and `long_reasoning` intents
- tiered attempt plans
- separate timeout dimensions:
  - `connect_timeout_seconds`
  - `write_timeout_seconds`
  - `first_byte_timeout_seconds`
  - `idle_timeout_seconds`
  - `total_deadline_seconds`
- escalation to a high token tier only after explicit failure signals such as `length`, empty answer, or invalid structured output

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py -q
```

Expected: FAIL because the current runtime policy only exposes thinking/non-thinking classes and fixed checkpoint arrays.

**Step 3: Write minimal implementation**

Refactor runtime policy generation to:

- accept task intent and prior attempt outcomes
- emit attempt tiers rather than a single default cap
- keep the current contract backward-compatible where possible, then update serialization tests where necessary

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/services/test_runtime_policy.py tests/transports/test_live_runner.py tests/test_cli_commands.py tests/webapi/test_run_orchestrator.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/services/runtime_policy.py \
  src/modelfingerprint/contracts/run.py \
  src/modelfingerprint/transports/live_runner.py \
  tests/services/test_runtime_policy.py \
  tests/transports/test_live_runner.py \
  tests/test_cli_commands.py \
  tests/webapi/test_run_orchestrator.py
git commit -m "refactor: make runtime policy intent-driven"
```

### Task 6: Add protocol-family live smoke baselines

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/e2e/test_live_endpoint_profiles.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/test_capability_probe_cli.py`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/docs/plans/2026-03-12-multi-protocol-transport-architecture-design.md`
- Create: `/Users/zhuangwei/Downloads/coding/modelfingerprint/docs/plans/2026-03-12-multi-protocol-transport-architecture-implementation-plan.md`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/e2e/test_live_endpoint_profiles.py`

**Step 1: Write the failing live smoke assertions**

Add representative smoke paths for:

- one OpenAI-compatible endpoint
- one provider/model that exercises profile quirks
- placeholders skipped by default for future Anthropic and Gemini-family live baselines

Also add assertions that framework latency and payload shape are compared against the simplest valid direct-request baseline rather than only against internal expectations.

**Step 2: Run test to verify it fails**

Run:

```bash
uv run pytest tests/e2e/test_live_endpoint_profiles.py tests/test_capability_probe_cli.py -q
```

Expected: FAIL because those baseline comparisons do not yet exist.

**Step 3: Write minimal implementation**

Update the live smoke tests so the repository has a repeatable compatibility baseline for future transport and adapter changes.

Keep real-provider credentials out of the repository and skip live-only cases unless the required environment is present.

**Step 4: Run test to verify it passes**

Run:

```bash
uv run pytest tests/e2e/test_live_endpoint_profiles.py tests/test_capability_probe_cli.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add tests/e2e/test_live_endpoint_profiles.py \
  tests/test_capability_probe_cli.py \
  docs/plans/2026-03-12-multi-protocol-transport-architecture-design.md \
  docs/plans/2026-03-12-multi-protocol-transport-architecture-implementation-plan.md
git commit -m "test: add protocol-family live compatibility baselines"
```

### Task 7: Run focused verification before any new protocol-family adapter work

**Files:**
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/http_client.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/dialects/openai_chat.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/dialects/quirks.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/runtime_policy.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_http_client.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_openai_chat_dialect.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_capability_probe.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_runtime_policy.py`

**Step 1: Run the focused regression suite**

Run:

```bash
uv run pytest \
  tests/transports/test_http_client.py \
  tests/transports/test_live_runner.py \
  tests/transports/test_openai_chat_dialect.py \
  tests/services/test_capability_probe.py \
  tests/services/test_runtime_policy.py \
  tests/test_cli_commands.py \
  tests/webapi/test_run_orchestrator.py -q
```

Expected: PASS

**Step 2: Run endpoint-profile validation**

Run:

```bash
uv run python -m modelfingerprint.cli validate-endpoints --root .
```

Expected: endpoint validation succeeds with the new profile fields and quirk declarations.

**Step 3: Run one representative direct live smoke**

Run a representative OpenAI-compatible smoke request against a configured live endpoint using both:

- the simplest direct request baseline
- the framework path

Expected: payload shape is equivalent and framework latency stays within an acceptable delta defined by the task.

**Step 4: Commit**

```bash
git add docs/plans/2026-03-12-multi-protocol-transport-architecture-design.md \
  docs/plans/2026-03-12-multi-protocol-transport-architecture-implementation-plan.md
git commit -m "docs: record multi-protocol transport implementation plan"
```
