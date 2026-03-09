from __future__ import annotations

from pathlib import Path

from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.storage.filesystem import ensure_directories


def test_repository_paths_resolve_from_root(tmp_path: Path) -> None:
    paths = RepositoryPaths(root=tmp_path)

    assert paths.root == tmp_path
    assert paths.prompt_bank_dir == tmp_path / "prompt-bank"
    assert paths.endpoint_profiles_dir == tmp_path / "endpoint-profiles"
    assert paths.profiles_dir == tmp_path / "profiles"
    assert paths.runs_dir == tmp_path / "runs"
    assert paths.calibration_dir == tmp_path / "calibration"
    assert paths.traces_dir == tmp_path / "traces"


def test_directories_are_created_only_on_explicit_request(tmp_path: Path) -> None:
    paths = RepositoryPaths(root=tmp_path)

    for path in (
        paths.prompt_bank_dir,
        paths.endpoint_profiles_dir,
        paths.profiles_dir,
        paths.runs_dir,
        paths.calibration_dir,
        paths.traces_dir,
    ):
        assert not path.exists()

    created = ensure_directories(
        paths.prompt_bank_dir,
        paths.endpoint_profiles_dir,
        paths.profiles_dir,
        paths.runs_dir,
        paths.calibration_dir,
        paths.traces_dir,
    )

    assert created == [
        paths.prompt_bank_dir,
        paths.endpoint_profiles_dir,
        paths.profiles_dir,
        paths.runs_dir,
        paths.calibration_dir,
        paths.traces_dir,
    ]
    for path in created:
        assert path.is_dir()
