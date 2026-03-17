English | [简体中文](./README.zh-CN.md)

# Model Fingerprint

Verify model identity and detect downgrades or swaps across LLM endpoints.

[Official Website](https://model-fingerprint.com/) · [Live Demo](https://model-fingerprint.com/) · [Web API Contract](./docs/apis/web_api_contract.md)

Model Fingerprint is a developer-facing toolkit for checking whether a claimed endpoint matches the fingerprint you selected. The repository includes the Python engine, CLI workflows, a Next.js web console, and thin `/api/v1` routes backed by the same engine.

## Why Teams Use It

- Verify vendor claims before routing production traffic
- Detect downgrades, swaps, and provider drift over time
- Compare a hosted endpoint against a pinned reference fingerprint
- Keep protocol compatibility and identity similarity separate

## Official Demo

The official demo is live at [model-fingerprint.com](https://model-fingerprint.com/). It exposes the same online detection workflow documented in this repository: list fingerprint models, start one live run, poll progress, fetch the terminal result, and cancel an in-flight run when needed.

The hosted workflow uses your API key only for the current check and does not store it after the request completes.

## Case: Mismatch

This case shows a claimed `anthropic/claude-haiku-4.5` endpoint checked against the `Claude Opus 4.6` fingerprint. The result is a formal `mismatch`, with `Claude Haiku 4.5` surfaced as the nearest candidate.

![Mismatch case from the official demo workflow](./docs/assets/readme/case-mismatch-claude-haiku-45-vs-opus-46.png)

- Claimed endpoint: `anthropic/claude-haiku-4.5` via `https://openrouter.ai/api/v1`
- Selected fingerprint: `Claude Opus 4.6`
- Reported evidence: fingerprint-range gap, capability consistency, and prompt-level similarity

## What's In This Repo

- Python engine and CLI for `run-suite`, `build-profile`, `calibrate`, and `compare`
- Next.js web console in `apps/web`
- Web API routes in `apps/web/app/api/v1`, backed by the Python bridge
- Checked-in calibration manifests, reference profiles, and offline quickstart fixtures

## Quickstart

### Try the hosted demo

Open [model-fingerprint.com](https://model-fingerprint.com/), choose a fingerprint model, point it at an OpenAI-compatible base URL, and start a live check.

### Run the web console locally

```bash
uv sync --extra dev
cd apps/web
pnpm install
pnpm dev
```

Then open `http://localhost:3000`. The Next.js app shells out to `uv run python -m modelfingerprint.webapi.bridge_cli`, so the local web console and the checked-in engine stay on the same contract.

### Run the offline CLI example

The public offline fixtures live under `examples/quickstart/quick-check-v3/`.

```bash
uv sync --extra dev

RUN_DATE=2026-03-11
EXAMPLES=examples/quickstart/quick-check-v3

uv run python -m modelfingerprint.cli validate-prompts --root .
uv run python -m modelfingerprint.cli validate-endpoints --root .

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label glm-5-a1 \
  --claimed-model glm-5 \
  --fixture-responses "$EXAMPLES/glm-5-a1.json" \
  --run-date "$RUN_DATE"
```

From there, use the same checked-in fixtures with `build-profile`, `calibrate`, and `compare` to walk the full file-based pipeline.

## How It Works

1. Build stable reference fingerprints from repeated baseline runs.
2. Execute a released suite against a suspect endpoint or offline fixtures.
3. Compare prompt, capability, and protocol evidence against pinned profiles.
4. Report a formal result when evidence is sufficient, otherwise fall back to provisional or incompatible states.

Model identity evidence and protocol compatibility are reported separately.

## Reading Results

- `formal_result`: enough usable evidence and a compatible protocol path
- `provisional`: partial evidence, useful for debugging but not final
- `insufficient_evidence`: too little usable signal to rank confidently
- `incompatible_protocol`: protocol mismatch blocks a normal comparison

Model Fingerprint produces evidence, not mathematical proof of identity. High similarity with low coverage should be treated cautiously.

## Repository Layout

- `examples/quickstart/quick-check-v3/`: public offline fixtures for the quickstart
- `prompt-bank/`: prompt definitions and released suites
- `endpoint-profiles/`: endpoint capability profiles keyed by dialect
- `profiles/` and `calibration/`: checked-in reference artifacts and manifests
- `src/modelfingerprint/`: CLI, contracts, services, transports, adapters, and Web API bridge
- `apps/web/`: web console, local API routes, and browser-side UX
- `tests/`: contract, unit, and end-to-end coverage

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
uv run mypy src

cd apps/web
pnpm test
```

## Docs

- [Web API Contract](./docs/apis/web_api_contract.md)
