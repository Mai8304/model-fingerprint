English | [简体中文](./README.zh-CN.md)

# Model Fingerprint

A file-based CLI for verifying whether two LLM endpoints likely expose the same underlying model.

## What It Verifies

Model Fingerprint helps platform teams verify whether two LLM endpoints likely represent the same underlying model, even when providers use different names, wrappers, or protocol behavior.

Typical use cases:

- Validate vendor claims about model identity
- Compare a managed endpoint against an internal reference baseline
- Detect provider or release drift over time

## How It Works

Model Fingerprint uses versioned probe suites and file-based artifacts to compare whether two endpoints likely expose the same underlying model.

1. Release a probe suite. A versioned suite defines the prompts and extractors used to produce comparable signals.
2. Run the suite against a target endpoint. Each execution produces a run artifact with normalized outputs, coverage, and protocol observations.
3. Build reference profiles from repeated runs. Profiles aggregate multiple runs for a known model into a more stable reference fingerprint.
4. Calibrate thresholds from known baselines. Calibration derives suite-specific thresholds instead of relying on fixed global cutoffs.
5. Compare a suspect run against reference profiles. The comparison reports similarity, coverage, protocol status, and a final verdict.

Model identity similarity and protocol compatibility are reported separately.

## Quickstart

Requirements:

- Python 3.12+
- `uv`

This example runs the full offline `quick-check-v3` flow with the checked-in fixtures under `examples/quickstart/quick-check-v3/`.

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

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label glm-5-a2 \
  --claimed-model glm-5 \
  --fixture-responses "$EXAMPLES/glm-5-a2.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label claude-ops-4.6-a1 \
  --claimed-model claude-ops-4.6 \
  --fixture-responses "$EXAMPLES/claude-ops-4.6-a1.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label claude-ops-4.6-a2 \
  --claimed-model claude-ops-4.6 \
  --fixture-responses "$EXAMPLES/claude-ops-4.6-a2.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli run-suite quick-check-v3 \
  --root . \
  --target-label suspect-v3 \
  --claimed-model glm-5 \
  --fixture-responses "$EXAMPLES/suspect.json" \
  --run-date "$RUN_DATE"

uv run python -m modelfingerprint.cli build-profile \
  --root . \
  --model-id glm-5 \
  --run "runs/$RUN_DATE/glm-5-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/glm-5-a2.quick-check-v3.json"

uv run python -m modelfingerprint.cli build-profile \
  --root . \
  --model-id claude-ops-4.6 \
  --run "runs/$RUN_DATE/claude-ops-4.6-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/claude-ops-4.6-a2.quick-check-v3.json"

uv run python -m modelfingerprint.cli calibrate \
  --root . \
  --profile profiles/quick-check-v3/glm-5.json \
  --profile profiles/quick-check-v3/claude-ops-4.6.json \
  --run "runs/$RUN_DATE/glm-5-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/glm-5-a2.quick-check-v3.json" \
  --run "runs/$RUN_DATE/claude-ops-4.6-a1.quick-check-v3.json" \
  --run "runs/$RUN_DATE/claude-ops-4.6-a2.quick-check-v3.json"

uv run python -m modelfingerprint.cli compare \
  --run "runs/$RUN_DATE/suspect-v3.quick-check-v3.json" \
  --profile profiles/quick-check-v3/glm-5.json \
  --profile profiles/quick-check-v3/claude-ops-4.6.json \
  --calibration calibration/quick-check-v3.json \
  --artifact-json > comparison.json
```

The resulting `comparison.json` should rank `glm-5` first and report a compatible protocol, for example:

```json
{
  "summary": {
    "top1_model": "glm-5",
    "verdict": "match"
  },
  "coverage": {
    "protocol_status": "compatible"
  }
}
```

Use `--json` instead of `--artifact-json` when you only need the compact comparison summary.

## Interpreting Results

- `top1_model` and `top1_similarity` identify the closest reference profile.
- `content_similarity` and `capability_similarity` summarize the strongest comparison signals.
- `answer_coverage_ratio`, `reasoning_coverage_ratio`, and `capability_coverage_ratio` tell you how much of the suite produced usable evidence.
- Read `protocol_status` and `verdict` together. A protocol problem is operational evidence, not automatic proof of a different model.

## Limitations

- Model Fingerprint produces evidence, not mathematical proof of identity.
- Verdict quality depends on the selected suite and the baseline runs used for calibration.
- High similarity with low coverage should be treated cautiously.
- Protocol incompatibility does not automatically mean the underlying model is different.

## CLI Overview

- `probe-capabilities`: probe a live endpoint and return observed capability signals
- `validate-prompts`: validate prompt definitions, suite references, and release subsets
- `validate-endpoints`: validate endpoint-profile YAML files
- `show-suite`: inspect a released suite from disk
- `show-run`: inspect a stored run artifact
- `show-profile`: inspect a stored profile artifact
- `run-suite`: execute a suite in offline fixture mode or live endpoint mode
- `build-profile`: aggregate repeated runs into a reference profile artifact
- `calibrate`: derive suite-specific thresholds from known baselines
- `compare`: compare a suspect run against reference profiles and emit a summary or full artifact

## Repository Layout

- `examples/quickstart/quick-check-v3/`: checked-in offline fixtures for the public quickstart
- `prompt-bank/`: prompt definitions and released suites
- `endpoint-profiles/`: endpoint capability profiles keyed by dialect
- `extractors/`: extractor descriptors
- `schemas/`: checked-in JSON Schemas for artifact contracts
- `src/modelfingerprint/`: CLI, contracts, services, transports, and adapters
- `tests/`: contract, unit, and end-to-end coverage

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```

## Further Docs

- `docs/apis/`: stable API and contract references
