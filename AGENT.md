# AGENT.md

Scope: repository guidance for coding agents working in this project.

Precedence:
1. Direct user instructions
2. This file
3. Current docs under `docs/plans/` and `docs/tasks/`

## Source of Truth

Read these before making changes:

- `docs/plans/2026-03-09-model-fingerprint-architecture-design.md`
- `docs/plans/2026-03-09-model-fingerprint-implementation-plan.md`

Follow task docs in this order unless the user explicitly changes priority:

1. `docs/tasks/2026-03-09-mf-p0-foundation-and-contracts.md`
2. `docs/tasks/2026-03-09-mf-p1-prompt-bank-and-extractors.md`
3. `docs/tasks/2026-03-09-mf-p2-profile-calibration-and-comparison.md`
4. `docs/tasks/2026-03-09-mf-p3-cli-reporting-and-e2e.md`

## Project Shape

- Keep protocol files versioned and file-based.
- Keep source files and generated artifacts separate.
- `screening-vN` must remain a strict subset of `default-vN`.
- Material prompt or extractor changes require a new version instead of silent in-place mutation.

## Tech Stack

Prefer the planned stack unless the user asks otherwise:

- Python 3.12+
- Typer
- Pydantic v2
- PyYAML
- jsonschema
- pytest
- Ruff
- mypy

## Working Rules

- Read the relevant task document before implementing.
- Prefer small, scoped changes.
- Prefer fixture-driven tests and fake transports for default development paths.
- Keep important protocol state on disk, not only in code or chat context.

## Verification

- Run the smallest relevant test set for the code you changed.
- Do not claim completion without verification.
- If you change contracts, schemas, extractors, comparison logic, or verdict rules, update or add tests in the same change.

## Documentation

- If architecture, contracts, versioning rules, or execution flow materially changes, update the relevant file under `docs/plans/` or `docs/tasks/`.
- Keep this file short; detailed design belongs in the docs.
