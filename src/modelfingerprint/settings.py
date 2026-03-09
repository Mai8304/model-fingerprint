from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


def resolve_repository_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()

    for path in (candidate, *candidate.parents):
        if (path / ".git").exists():
            return path

    raise FileNotFoundError("Could not locate repository root from the given path.")


@dataclass(frozen=True)
class RepositoryPaths:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())

    @classmethod
    def from_working_directory(cls, start: Path | None = None) -> RepositoryPaths:
        return cls(root=resolve_repository_root(start))

    @property
    def prompt_bank_dir(self) -> Path:
        return self.root / "prompt-bank"

    @property
    def profiles_dir(self) -> Path:
        return self.root / "profiles"

    @property
    def runs_dir(self) -> Path:
        return self.root / "runs"

    @property
    def calibration_dir(self) -> Path:
        return self.root / "calibration"

