# AGENT.md

Scope: repository guidance for coding agents working in this project.

Precedence:
1. Direct user instructions
2. This file
3. Code, contracts, and tests for the surface being changed
4. Supporting docs under `README*` and `docs/`

## Read First

- `README.md` / `README.zh-CN.md`: product scope, CLI flow, repository layout
- `docs/apis/web_api_contract.md`: web API contract and `api_key` boundary
- `.codex/skills/modelfingerprint-server-deploy/SKILL.md`: required workflow before any production server deployment
- `src/modelfingerprint/contracts/*.py` and `schemas/*.json`: artifact contract source of truth
- `prompt-bank/`, `extractors/`, `endpoint-profiles/`: versioned prompt, extractor, and endpoint inputs
- `src/modelfingerprint/webapi/*.py` and `apps/web/lib/api-contract.ts`: Python/web boundary types
- `docs/plans/*.md`: design context only; do not let stale plan docs override code or tests

## Repository Shape

- `src/modelfingerprint/`: Python engine, CLI, contracts, transports, and web bridge/orchestration
- `apps/web/`: Next.js UI and route handlers that call the Python bridge
- Checked-in artifacts under `examples/`, `profiles/`, `calibration/`, and `schemas/` are part of the product surface
- Treat `.webapi/`, `runs/`, `traces/`, and `output/` as data directories; do not rewrite or clean them unless the task requires it

## Deployment Environment

- Public production URL: `https://model-fingerprint.com`
- Origin server: `43.162.106.125` (`ubuntu`)
- Local SSH key path for this repo: `/Users/zhuangwei/Downloads/coding/modelfingerprint/modelfingerprint.pem`
- Never copy, print, upload, or commit PEM contents; use the local key file with `ssh -i ...`
- Remote repo root: `/home/ubuntu/modelfingerprint`
- Remote web working directory: `/home/ubuntu/modelfingerprint/apps/web`
- Web process: `modelfingerprint-web` systemd service
- Reverse proxy/TLS: `nginx` serves `model-fingerprint.com`, terminates HTTPS on `443`, and proxies to `http://127.0.0.1:3000`
- Deployment order must be serial, not parallel:
  1. Sync workspace to `/home/ubuntu/modelfingerprint`
  2. Run remote `pnpm build` inside `/home/ubuntu/modelfingerprint/apps/web`
  3. Restart `modelfingerprint-web`
  4. Smoke-check `https://model-fingerprint.com` and `/api/v1/fingerprints`

## Working Rules

- Keep Python and HTTP payload keys `snake_case` at the contract boundary
- Never log, persist, return, or commit secrets, `api_key` values, PEM material, or `.env` contents
- Prefer additive or versioned changes for released suites, extractor IDs, schemas, and comparison semantics; avoid silent in-place behavior changes
- When creating git commits, keep them atomic: one logical change per commit, with matching tests/docs in the same commit
- If you change prompts, extractors, endpoint profiles, contracts, calibration logic, verdict logic, or web API payloads, update relevant tests and docs in the same change
- Prefer small diffs and search with `rg`; do not delete checked-in reference artifacts as cleanup unless explicitly asked

## Verification

- Python changes: run the smallest relevant `uv run pytest ...`; add `uv run ruff check src tests` and `uv run mypy src` when contracts, typing, or core services change
- Web changes: run the smallest relevant `pnpm --dir apps/web test ...`; add `pnpm --dir apps/web build` when Next.js routes, config, or build-time behavior changes
- Cross-boundary changes to bridge, shared contracts, or API shapes: run both Python and web verification
