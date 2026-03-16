---
name: modelfingerprint-server-deploy
description: Use when deploying this repository to the production server, restarting modelfingerprint-web, or validating a server deploy after backend, UI, profile, or model-catalog changes.
---

# Modelfingerprint Server Deploy

## Overview

Deploy this repository to `https://model-fingerprint.com` without regressing the UI, model catalog, or backend runtime.

This workflow exists because the production server is a plain directory, not a git checkout. A deploy is only as correct as the local workspace you choose to rsync.

## When to Use

- Any production deploy to `43.162.106.125`
- Any restart of `modelfingerprint-web`
- Any deploy after changing `apps/web/`, `src/modelfingerprint/`, `profiles/`, `endpoint-profiles/`, or `calibration/`
- Any incident where the site shows the wrong UI, wrong model count, or suspiciously old backend behavior

Do not use this skill for local dev runs or test-only work.

## Hard Rules

1. Choose the deploy source explicitly. Never rsync an isolated worktree unless the user explicitly wants that exact snapshot online.
2. Treat the local workspace as the source of truth. The remote directory is not a git repo and cannot tell you what branch or commit it represents.
3. Deploy serially: sync, install, build, restart, smoke-check. Do not overlap these steps.
4. Do not declare failure from an immediate `502` during restart. Check service state, wait briefly, then re-test.
5. Validate both backend markers and catalog/UI shape after deploy. A green restart alone is not enough.

## Preflight

Run these from the workspace you intend to deploy.

```bash
pwd
git rev-parse --short HEAD
git branch --show-current
git status --short
find endpoint-profiles -maxdepth 1 -name '*.yaml' | wc -l
find profiles/fingerprint-suite-v3 -maxdepth 1 -name '*.json' | wc -l
rg -n 'RUNTIME_POLICY_ID|intent_tiered_runtime_v1' src/modelfingerprint/services/runtime_policy.py
rg -n '^import httpx|httpx\\.' src/modelfingerprint/transports/http_client.py
```

Interpretation:

- If `git status --short` is dirty, say explicitly that you are deploying a dirty workspace snapshot.
- If the profile counts or backend markers do not match the intended release, stop and fix the source workspace first.
- If you were working in a temporary worktree, compare it against the main workspace before deploying.

## Deploy

```bash
rsync -az --delete \
  --exclude '.git' \
  --exclude '.worktrees' \
  --exclude '.venv' \
  --exclude '.pytest_cache' \
  --exclude '.ruff_cache' \
  --exclude '.mypy_cache' \
  --exclude '.webapi' \
  --exclude 'runs' \
  --exclude 'traces' \
  --exclude 'output' \
  --exclude 'apps/web/node_modules' \
  --exclude 'apps/web/.next' \
  -e 'ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem -o StrictHostKeyChecking=no' \
  /Users/zhuangwei/Downloads/coding/modelfingerprint/ \
  ubuntu@43.162.106.125:/home/ubuntu/modelfingerprint/
```

```bash
ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem -o StrictHostKeyChecking=no \
  ubuntu@43.162.106.125 '
    set -euo pipefail
    export PATH="$HOME/.local/bin:$PATH"
    cd /home/ubuntu/modelfingerprint
    uv sync --frozen
    pnpm --dir apps/web install --frozen-lockfile
    pnpm --dir apps/web build
    sudo systemctl restart modelfingerprint-web
    systemctl is-active modelfingerprint-web
  '
```

## Post-Deploy Verification

Verify all of these before claiming success.

### 1. Remote backend markers

```bash
ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem -o StrictHostKeyChecking=no \
  ubuntu@43.162.106.125 '
    set -euo pipefail
    cd /home/ubuntu/modelfingerprint
    grep -nE "RUNTIME_POLICY_ID|intent_tiered_runtime_v1" src/modelfingerprint/services/runtime_policy.py
    grep -nE "^import httpx|httpx\\." src/modelfingerprint/transports/http_client.py | head -n 10
  '
```

### 2. Local origin health and model count

```bash
ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem -o StrictHostKeyChecking=no \
  ubuntu@43.162.106.125 '
    set -euo pipefail
    python3 - <<'"'"'PY'"'"'
import json, urllib.request
payload = json.load(urllib.request.urlopen("http://127.0.0.1:3000/api/v1/fingerprints"))
items = payload["items"] if isinstance(payload, dict) else payload
print("fingerprints", len(items))
print("first_two_ids", [item["id"] for item in items[:2]])
PY
  '
```

### 3. External smoke

```bash
curl -I https://model-fingerprint.com
```

If the site just restarted and returns `502`, do this before escalating:

```bash
ssh -i /Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem -o StrictHostKeyChecking=no \
  ubuntu@43.162.106.125 '
    systemctl is-active modelfingerprint-web
    sudo journalctl -u modelfingerprint-web -n 80 --no-pager
    sudo tail -n 40 /var/log/nginx/error.log
  '
sleep 10
curl -I https://model-fingerprint.com
```

## Recovery Patterns

### Wrong UI or wrong model count after deploy

Likely cause: the wrong local workspace or worktree was deployed.

Response:

1. Stop debugging the remote first.
2. Re-verify local source counts and sentinels.
3. Re-deploy from the correct workspace.

### New backend not visible on server

Likely cause: the right feature branch was tested locally, but an older main workspace was deployed.

Response:

1. Verify the local source workspace contains the intended backend markers.
2. Verify the remote copies of those same files.
3. Re-deploy from the workspace that actually contains the merged backend.

### Immediate 502 after restart

Likely cause: transient app startup lag behind nginx.

Response:

1. Check `systemctl is-active modelfingerprint-web`.
2. Check recent `journalctl` and nginx errors.
3. Wait briefly, then retry smoke before declaring deploy failure.

## Anti-Patterns This Skill Prevents

- Deploying directly from a temporary worktree snapshot and silently regressing UI/catalog files
- Assuming the remote server knows which branch it is on
- Treating `systemctl restart` success as sufficient evidence
- Treating a transient restart-window `502` as a permanent outage
- Verifying only the homepage and not the fingerprint registry shape
