# Live Transport Monitoring Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Route non-streaming live JSON requests through blocking execution, keep monitoring only for true streaming requests, widen streaming no-data checkpoints to 60 seconds, verify the failing live endpoint now succeeds, and then deploy the change to the production server.

**Architecture:** Keep request-mode selection inside `LiveRunner` so the rest of the system still sees the same endpoint profile and runtime policy contracts. Runtime policy continues to describe timeout budgets, but request execution mode is derived from the concrete outbound request. True streaming requests retain in-flight monitoring; blocking JSON requests use the existing send path with the runtime policy's total deadline as the read budget.

**Tech Stack:** Python, Pydantic, Typer, pytest, uv, systemd, rsync or scp, pnpm

---

### Task 1: Update runtime policy checkpoints

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/runtime_policy.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_runtime_policy.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_runtime_policy.py`

**Step 1: Write the failing test**

Update runtime policy tests to assert:

- thinking no-data checkpoints are `[60, 90]`
- non-thinking no-data checkpoints are `[60]`
- total deadline remains `120`

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_runtime_policy.py -q`
Expected: FAIL because the current checkpoints are `[30, 60]` and `[30]`.

**Step 3: Write minimal implementation**

Update the checkpoint constants in `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/runtime_policy.py`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_runtime_policy.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/services/runtime_policy.py tests/services/test_runtime_policy.py
git commit -m "fix: widen live no-data checkpoints"
```

### Task 2: Route blocking JSON requests through `send()`

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_live_runner.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_live_runner.py`

**Step 1: Write the failing test**

Add transport tests that assert:

- when runtime policy is present and the request is normal JSON, `LiveRunner` uses `send()`
- when runtime policy is present and the request is SSE or `stream: true`, `LiveRunner` still uses `start()+monitor`
- monitored request wait calls now use `60.0`

Use separate scripted doubles for blocking and monitored clients so the test can prove which method was called.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/transports/test_live_runner.py -q`
Expected: FAIL because runtime-policy execution currently always starts monitored in-flight requests.

**Step 3: Write minimal implementation**

In `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`:

- add a small request-mode classifier based on:
  - `Accept: text/event-stream`
  - JSON body `stream: true`
- use `_send_request(..., read_timeout_seconds=self._runtime_policy.total_deadline_seconds)` for non-streaming requests
- keep `_start_request()` and `_monitor_inflight_request()` only for streaming requests
- preserve current parse and attempt-summary behavior

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/transports/test_live_runner.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/modelfingerprint/transports/live_runner.py tests/transports/test_live_runner.py
git commit -m "fix: monitor only true streaming live requests"
```

### Task 3: Update runtime policy serialization expectations

**Files:**
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/test_cli_commands.py`
- Modify: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/test_cli_commands.py`
- Test: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`

**Step 1: Write the failing test**

Update tests that serialize or assert runtime policy snapshots to expect:

- non-thinking checkpoints `[60]`
- thinking checkpoints `[60, 90]`

Do not change the surrounding API contract shape.

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_cli_commands.py tests/webapi/test_run_orchestrator.py -q`
Expected: FAIL because fixtures and assertions still expect the old checkpoint values.

**Step 3: Write minimal implementation**

Adjust the affected assertions and, if needed, any helper payloads in:

- `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/test_cli_commands.py`
- `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_cli_commands.py tests/webapi/test_run_orchestrator.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_cli_commands.py tests/webapi/test_run_orchestrator.py
git commit -m "test: update runtime policy checkpoint expectations"
```

### Task 4: Run targeted verification and live repro

**Files:**
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/services/runtime_policy.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/src/modelfingerprint/transports/live_runner.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/services/test_runtime_policy.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/transports/test_live_runner.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/test_cli_commands.py`
- Verify only: `/Users/zhuangwei/Downloads/coding/modelfingerprint/tests/webapi/test_run_orchestrator.py`

**Step 1: Run the targeted pytest set**

Run:

```bash
uv run pytest \
  tests/services/test_runtime_policy.py \
  tests/transports/test_live_runner.py \
  tests/test_cli_commands.py \
  tests/webapi/test_run_orchestrator.py -q
```

Expected: PASS

**Step 2: Re-run the previously failing live suite**

Run:

```bash
uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label diag-claude-opus-4-6 \
  --claimed-model claude-opus-4-6 \
  --base-url http://newapi.200m.997555.xyz/v1 \
  --api-key '<ROTATED_API_KEY>' \
  --model claude-opus-4-6 \
  --run-date 2026-03-12
```

Expected: the run artifact is written successfully and prompt attempts no longer fail with `no_data_checkpoint_exceeded` for plain JSON requests.

**Step 3: Inspect the resulting run**

Run:

```bash
uv run python -m modelfingerprint.cli show-run \
  /Users/zhuangwei/Downloads/coding/modelfingerprint/runs/2026-03-12/diag-claude-opus-4-6.quick-check-v3.json
```

Expected: normal run summary output instead of zero answer coverage caused by timeout aborts.

**Step 4: Commit**

```bash
git add src/modelfingerprint/services/runtime_policy.py src/modelfingerprint/transports/live_runner.py \
  tests/services/test_runtime_policy.py tests/transports/test_live_runner.py \
  tests/test_cli_commands.py tests/webapi/test_run_orchestrator.py \
  docs/plans/2026-03-12-live-transport-monitoring-design.md \
  docs/plans/2026-03-12-live-transport-monitoring-implementation-plan.md
git commit -m "fix: align live monitoring with request transport mode"
```

### Task 5: Deploy to production server and smoke-check

**Files:**
- Verify remote app root: `/home/ubuntu/modelfingerprint`
- Verify remote web app: `/home/ubuntu/modelfingerprint/apps/web`

**Step 1: Sync the workspace to the server**

Run:

```bash
rsync -az --delete \
  -e "ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem" \
  /Users/zhuangwei/Downloads/coding/modelfingerprint/ \
  ubuntu@43.162.106.125:/home/ubuntu/modelfingerprint/
```

Expected: sync completes without SSH or permission errors.

**Step 2: Build the web app remotely**

Run:

```bash
ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem \
  ubuntu@43.162.106.125 \
  "cd /home/ubuntu/modelfingerprint/apps/web && pnpm build"
```

Expected: `pnpm build` exits successfully.

**Step 3: Restart the web service**

Run:

```bash
ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem \
  ubuntu@43.162.106.125 \
  "sudo systemctl restart modelfingerprint-web && sudo systemctl status modelfingerprint-web --no-pager"
```

Expected: service is active after restart.

**Step 4: Smoke-check production**

Run:

```bash
curl -I https://model-fingerprint.com
curl -sS https://model-fingerprint.com/api/v1/fingerprints | head
```

Expected: the site responds over HTTPS and the API endpoint returns a successful payload.
