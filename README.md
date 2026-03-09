# Model Fingerprint

Standalone CLI toolkit for building and comparing file-based model
fingerprints from versioned probe suites.

The current v2 architecture is:

- thinking-aware
- dialect-driven with endpoint-profile configuration
- coverage-aware and protocol-aware
- fully file-based for runs, traces, profiles, and calibration artifacts

The design and phased implementation plan live under `docs/plans/` and
`docs/tasks/`.

## Repository Layout

- `prompt-bank/`: prompt definitions and released suites
- `endpoint-profiles/`: endpoint capability profiles keyed by dialect
- `extractors/`: extractor descriptors
- `schemas/`: checked-in JSON Schemas for artifact contracts
- `traces/`: live request/response traces keyed by run id
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

Validate the released prompt bank:

```bash
uv run python -m modelfingerprint.cli validate-prompts --root .
```

Validate endpoint profiles:

```bash
uv run python -m modelfingerprint.cli validate-endpoints --root .
```

Run a suite offline through fixture responses:

```bash
uv run python -m modelfingerprint.cli run-suite quick-check-v1 \
  --root . \
  --target-label suspect-a \
  --claimed-model gpt-5.3 \
  --fixture-responses path/to/responses.json \
  --run-date 2026-03-09
```

Run the same suite live through an endpoint profile:

```bash
export MODEL_FINGERPRINT_API_KEY=your-api-key
uv run python -m modelfingerprint.cli run-suite quick-check-v1 \
  --root . \
  --target-label suspect-a \
  --claimed-model gpt-5.3 \
  --endpoint-profile siliconflow-openai-chat \
  --run-date 2026-03-09
```

Build profiles from stored runs:

```bash
uv run python -m modelfingerprint.cli build-profile \
  --root . \
  --model-id gpt-5.3 \
  --run runs/2026-03-09/gpt-a1.quick-check-v1.json \
  --run runs/2026-03-09/gpt-a2.quick-check-v1.json
```

Calibrate a suite from baseline runs and profiles:

```bash
uv run python -m modelfingerprint.cli calibrate \
  --root . \
  --profile profiles/quick-check-v1/gpt-5.3.json \
  --profile profiles/quick-check-v1/claude-ops-4.6.json \
  --run runs/2026-03-09/gpt-a1.quick-check-v1.json \
  --run runs/2026-03-09/gpt-a2.quick-check-v1.json \
  --run runs/2026-03-09/claude-a1.quick-check-v1.json \
  --run runs/2026-03-09/claude-a2.quick-check-v1.json
```

Compare a suspect run to known profiles:

```bash
uv run python -m modelfingerprint.cli compare \
  --run runs/2026-03-09/suspect-a.quick-check-v1.json \
  --profile profiles/quick-check-v1/gpt-5.3.json \
  --profile profiles/quick-check-v1/claude-ops-4.6.json \
  --calibration calibration/quick-check-v1.json \
  --json
```

The comparison JSON now reports:

- overall similarity
- answer / reasoning / transport / surface similarity
- answer / reasoning coverage ratios
- protocol status and protocol issues
- verdict

Interpretation rule:

- `protocol_status = incompatible_protocol` means the endpoint could not honor the released protocol cleanly
- that is operational evidence, not automatic proof that the underlying model identity is different
- identity similarity and protocol compatibility are intentionally reported separately

## Commands

- `validate-prompts`: validate prompt definitions, suite references, and subset rules
- `validate-endpoints`: validate endpoint-profile YAML files
- `show-suite`: inspect a released suite from disk
- `show-run`: inspect a stored run artifact, including coverage and protocol status
- `show-profile`: inspect a stored profile artifact, including reasoning coverage and prompt weights
- `run-suite`: execute a suite in fixture mode or live endpoint-profile mode
- `build-profile`: aggregate repeated runs into one profile artifact
- `calibrate`: derive suite thresholds plus coverage thresholds from baseline runs
- `compare`: rank profiles against a target run and emit a coverage-aware verdict
