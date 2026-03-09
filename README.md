# Model Fingerprint

Standalone CLI toolkit for building and comparing file-based model
fingerprints from versioned probe suites.

The design and phased implementation plan live under `docs/plans/` and
`docs/tasks/`.

## Repository Layout

- `prompt-bank/`: candidate prompts and released suites
- `extractors/`: extractor descriptors
- `schemas/`: checked-in JSON Schemas for artifact contracts
- `src/modelfingerprint/`: CLI, services, extractors, and adapters
- `tests/`: contract, unit, and end-to-end coverage

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
uv run mypy src
```

## Operator Flow

Validate the prompt bank:

```bash
uv run python -m modelfingerprint.cli validate-prompts --root .
```

Run a suite offline through fixture responses:

```bash
uv run python -m modelfingerprint.cli run-suite screening-v1 \
  --root . \
  --target-label suspect-a \
  --claimed-model gpt-5.3 \
  --fixture-responses path/to/responses.json \
  --run-date 2026-03-09
```

Build profiles from stored runs:

```bash
uv run python -m modelfingerprint.cli build-profile \
  --root . \
  --model-id gpt-5.3 \
  --run runs/2026-03-09/gpt-a1.screening-v1.json \
  --run runs/2026-03-09/gpt-a2.screening-v1.json
```

Calibrate a suite from baseline runs and profiles:

```bash
uv run python -m modelfingerprint.cli calibrate \
  --root . \
  --profile profiles/screening-v1/gpt-5.3.json \
  --profile profiles/screening-v1/claude-ops-4.6.json \
  --run runs/2026-03-09/gpt-a1.screening-v1.json \
  --run runs/2026-03-09/gpt-a2.screening-v1.json \
  --run runs/2026-03-09/claude-a1.screening-v1.json \
  --run runs/2026-03-09/claude-a2.screening-v1.json
```

Compare a suspect run to known profiles:

```bash
uv run python -m modelfingerprint.cli compare \
  --run runs/2026-03-09/suspect-a.screening-v1.json \
  --profile profiles/screening-v1/gpt-5.3.json \
  --profile profiles/screening-v1/claude-ops-4.6.json \
  --calibration calibration/screening-v1.json \
  --json
```

## Commands

- `validate-prompts`: validate candidate prompts, suite references, and subset rules
- `show-suite`: inspect a released suite from disk
- `show-run`: inspect a stored run artifact
- `show-profile`: inspect a stored profile artifact
- `run-suite`: execute a suite through a pluggable chat-completion transport
- `build-profile`: aggregate repeated runs into one profile artifact
- `calibrate`: derive suite thresholds from baseline runs
- `compare`: rank profiles against a target run and emit a verdict
