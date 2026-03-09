# Model Fingerprint Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a standalone file-based model fingerprinting toolkit that runs versioned probe suites, extracts structured features, builds canonical profiles, calibrates thresholds, and compares suspect endpoints against the fingerprint library.

**Architecture:** The project is a Python CLI application with versioned prompt-bank files, a fixed set of extractor families, immutable run artifacts, robust-statistics profile generation, suite-specific calibration, and open-set comparison. All protocol definitions and outputs live on disk so results remain reproducible and auditable without a database.

**Tech Stack:** Python 3.12+, Typer, Pydantic v2, PyYAML, jsonschema, pytest, Ruff, mypy

---

## Delivery Order

Implement in this order:

1. [P0 Foundation and Contracts](/Users/zhuangwei/Downloads/coding/modelfingerprint/docs/tasks/2026-03-09-mf-p0-foundation-and-contracts.md)
2. [P1 Prompt Bank and Extractors](/Users/zhuangwei/Downloads/coding/modelfingerprint/docs/tasks/2026-03-09-mf-p1-prompt-bank-and-extractors.md)
3. [P2 Profiles, Calibration, and Comparison](/Users/zhuangwei/Downloads/coding/modelfingerprint/docs/tasks/2026-03-09-mf-p2-profile-calibration-and-comparison.md)
4. [P3 CLI, Reporting, and End-to-End Flows](/Users/zhuangwei/Downloads/coding/modelfingerprint/docs/tasks/2026-03-09-mf-p3-cli-reporting-and-e2e.md)

## Milestone Intent

### Milestone A: Repository and protocol contracts exist

Outcome:
- repository is initialized
- package layout is present
- schema-validated prompt, run, profile, and calibration contracts exist
- a basic CLI entrypoint is in place

Acceptance anchor:
- `pytest tests/test_cli_smoke.py tests/contracts -q` passes

### Milestone B: Prompt bank and extractor pipeline exist

Outcome:
- candidate and suite files validate
- all five extractor families work on fixtures
- feature extraction is deterministic on fixture inputs

Acceptance anchor:
- `pytest tests/prompt_bank tests/extractors -q` passes

### Milestone C: Fingerprint math exists

Outcome:
- run artifacts can be aggregated into model profiles
- calibration files are computed from baseline runs
- comparison produces Top1, Top2, margin, claimed-model similarity, consistency, and verdict

Acceptance anchor:
- `pytest tests/profile tests/calibration tests/comparison -q` passes

### Milestone D: Operators can use the tool end-to-end

Outcome:
- CLI validates protocol files
- CLI runs suites
- CLI builds profiles
- CLI calibrates thresholds
- CLI compares target runs to profiles

Acceptance anchor:
- `pytest tests/e2e tests/test_cli_commands.py -q` passes

## Guardrails

1. Keep the project independent from OpenWhale code, naming, runtime dependencies, and deployment assumptions.
2. Freeze `default-v1` and `screening-v1` once released; future prompt updates must go through `default-v2`.
3. Do not let screening suites drift away from the full suite; `screening-vN` must always be a strict subset of `default-vN`.
4. Keep all important state on disk as JSON or YAML artifacts.
5. Prefer fixture-driven tests over real upstream calls during development.

## Handoff

Detailed phase plans live in `docs/tasks/` and are ordered for sequential implementation. Execute them in order; later phases assume earlier contracts already exist.
