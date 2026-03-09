from __future__ import annotations

from pathlib import Path


def ensure_directories(*paths: Path) -> list[Path]:
    created: list[Path] = []

    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)

    return created
