from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import Field, field_validator

from modelfingerprint.contracts._common import ContractModel, PromptId, SuiteId
from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.prompt import SuiteDefinition
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.prompt_bank import load_candidate_prompts, load_suites
from modelfingerprint.settings import RepositoryPaths

WEB_FINGERPRINT_SUITE_ID = "fingerprint-suite-v32"
WEB_FINGERPRINT_CHAIN_MANIFEST = "fingerprint-suite-v32.manifest.json"


class FingerprintChainError(RuntimeError):
    """Raised when the deployed web fingerprint chain is incomplete or inconsistent."""


class _PinnedFile(ContractModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class _PinnedSuiteDefinition(_PinnedFile):
    prompt_ids: list[PromptId] = Field(min_length=1)


class _PinnedPromptFile(_PinnedFile):
    prompt_id: PromptId


class _PinnedModelArtifact(_PinnedFile):
    model_id: str = Field(min_length=1)


class _WebFingerprintChainManifest(ContractModel):
    suite_id: SuiteId
    suite_definition: _PinnedSuiteDefinition
    prompt_files: list[_PinnedPromptFile] = Field(min_length=1)
    baseline_runs: list[_PinnedModelArtifact] = Field(min_length=1)
    profiles: list[_PinnedModelArtifact] = Field(min_length=1)
    calibration: _PinnedFile

    @field_validator("prompt_files")
    @classmethod
    def validate_unique_prompts(
        cls,
        value: list[_PinnedPromptFile],
    ) -> list[_PinnedPromptFile]:
        prompt_ids = [item.prompt_id for item in value]
        if len(prompt_ids) != len(set(prompt_ids)):
            raise ValueError("prompt_files must not contain duplicate prompt ids")
        return value

    @field_validator("baseline_runs", "profiles")
    @classmethod
    def validate_unique_models(
        cls,
        value: list[_PinnedModelArtifact],
    ) -> list[_PinnedModelArtifact]:
        model_ids = [item.model_id for item in value]
        if len(model_ids) != len(set(model_ids)):
            raise ValueError("model artifacts must not contain duplicate model ids")
        return value


@dataclass(frozen=True)
class WebFingerprintChain:
    suite: SuiteDefinition
    profiles: list[ProfileArtifact]
    calibration: CalibrationArtifact
    baseline_runs: dict[str, RunArtifact]

    @property
    def model_ids(self) -> list[str]:
        return [profile.model_id for profile in self.profiles]


def load_web_fingerprint_chain(paths: RepositoryPaths) -> WebFingerprintChain:
    manifest = _load_manifest(paths)
    if manifest.suite_id != WEB_FINGERPRINT_SUITE_ID:
        raise FingerprintChainError(
            f"web fingerprint manifest must pin {WEB_FINGERPRINT_SUITE_ID}, got {manifest.suite_id}"
        )

    suite = _load_and_validate_suite(paths, manifest)
    _load_and_validate_prompt_files(paths, manifest, suite)
    calibration = _load_and_validate_calibration(paths, manifest)
    profiles = _load_and_validate_profiles(paths, manifest, suite)
    baseline_runs = _load_and_validate_baseline_runs(paths, manifest, suite, set(_profile_map(profiles)))

    if set(_profile_map(profiles)) != set(baseline_runs):
        raise FingerprintChainError(
            "baseline run set does not match pinned profile set: "
            f"profiles={sorted(_profile_map(profiles))}, runs={sorted(baseline_runs)}"
        )

    return WebFingerprintChain(
        suite=suite,
        profiles=profiles,
        calibration=calibration,
        baseline_runs=baseline_runs,
    )


def _load_manifest(paths: RepositoryPaths) -> _WebFingerprintChainManifest:
    manifest_path = paths.calibration_dir / WEB_FINGERPRINT_CHAIN_MANIFEST
    if not manifest_path.exists():
        raise FingerprintChainError(
            f"missing web fingerprint chain manifest: {manifest_path}"
        )
    return _WebFingerprintChainManifest.model_validate(
        json.loads(manifest_path.read_text(encoding="utf-8"))
    )


def _load_and_validate_suite(
    paths: RepositoryPaths,
    manifest: _WebFingerprintChainManifest,
) -> SuiteDefinition:
    suite_path = _resolve_repo_path(paths.root, manifest.suite_definition.path)
    _validate_pinned_file(suite_path, manifest.suite_definition.sha256)

    suites = load_suites(paths.prompt_bank_dir / "suites")
    try:
        suite = suites[manifest.suite_id]
    except KeyError as exc:
        raise FingerprintChainError(f"missing pinned suite: {manifest.suite_id}") from exc

    if suite.prompt_ids != manifest.suite_definition.prompt_ids:
        raise FingerprintChainError(
            "suite prompt ids drifted from manifest: "
            f"{suite.prompt_ids} != {manifest.suite_definition.prompt_ids}"
        )
    return suite


def _load_and_validate_prompt_files(
    paths: RepositoryPaths,
    manifest: _WebFingerprintChainManifest,
    suite: SuiteDefinition,
) -> None:
    candidate_prompts = load_candidate_prompts(paths.prompt_bank_dir / "candidates")
    pinned_prompt_ids = [item.prompt_id for item in manifest.prompt_files]
    if pinned_prompt_ids != suite.prompt_ids:
        raise FingerprintChainError(
            "pinned prompt files do not exactly match the web suite prompt ids"
        )

    for item in manifest.prompt_files:
        prompt_path = _resolve_repo_path(paths.root, item.path)
        _validate_pinned_file(prompt_path, item.sha256)
        prompt = candidate_prompts.get(item.prompt_id)
        if prompt is None:
            raise FingerprintChainError(f"missing pinned prompt definition: {item.prompt_id}")
        if prompt.id != item.prompt_id:
            raise FingerprintChainError(f"prompt id mismatch for {prompt_path}")


def _load_and_validate_calibration(
    paths: RepositoryPaths,
    manifest: _WebFingerprintChainManifest,
) -> CalibrationArtifact:
    calibration_path = _resolve_repo_path(paths.root, manifest.calibration.path)
    _validate_pinned_file(calibration_path, manifest.calibration.sha256)
    calibration = CalibrationArtifact.model_validate(
        json.loads(calibration_path.read_text(encoding="utf-8"))
    )
    if calibration.suite_id != manifest.suite_id:
        raise FingerprintChainError(
            f"calibration suite mismatch: {calibration.suite_id} != {manifest.suite_id}"
        )
    return calibration


def _load_and_validate_profiles(
    paths: RepositoryPaths,
    manifest: _WebFingerprintChainManifest,
    suite: SuiteDefinition,
) -> list[ProfileArtifact]:
    expected_profile_paths = {
        _resolve_repo_path(paths.root, item.path): item for item in manifest.profiles
    }
    profile_dir = paths.profiles_dir / manifest.suite_id
    actual_profile_paths = sorted(profile_dir.glob("*.json"))
    unexpected_profiles = [
        path.name for path in actual_profile_paths if path not in expected_profile_paths
    ]
    if unexpected_profiles:
        raise FingerprintChainError(
            "unexpected profile artifacts present outside the pinned web chain: "
            + ", ".join(unexpected_profiles)
        )

    profiles: list[ProfileArtifact] = []
    for path, item in sorted(expected_profile_paths.items(), key=lambda entry: entry[1].model_id):
        _validate_pinned_file(path, item.sha256)
        profile = ProfileArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))
        _validate_profile(profile, item.model_id, suite)
        profiles.append(profile)
    return profiles


def _load_and_validate_baseline_runs(
    paths: RepositoryPaths,
    manifest: _WebFingerprintChainManifest,
    suite: SuiteDefinition,
    expected_models: set[str],
) -> dict[str, RunArtifact]:
    runs: dict[str, RunArtifact] = {}
    for item in manifest.baseline_runs:
        path = _resolve_repo_path(paths.root, item.path)
        _validate_pinned_file(path, item.sha256)
        run = RunArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))
        _validate_baseline_run(run, item.model_id, suite)
        runs[item.model_id] = run

    missing_models = sorted(expected_models - set(runs))
    if missing_models:
        raise FingerprintChainError(
            "missing pinned baseline runs for models: " + ", ".join(missing_models)
        )
    return runs


def _validate_profile(
    profile: ProfileArtifact,
    expected_model_id: str,
    suite: SuiteDefinition,
) -> None:
    if profile.model_id != expected_model_id:
        raise FingerprintChainError(
            f"profile model id mismatch: {profile.model_id} != {expected_model_id}"
        )
    if profile.suite_id != suite.id:
        raise FingerprintChainError(
            f"profile suite mismatch for {expected_model_id}: {profile.suite_id} != {suite.id}"
        )
    profile_prompt_ids = [prompt.prompt_id for prompt in profile.prompts]
    if sorted(profile_prompt_ids) != sorted(suite.prompt_ids):
        raise FingerprintChainError(
            f"profile prompt set mismatch for {expected_model_id}: {profile_prompt_ids}"
        )
    if profile.answer_coverage_ratio is not None and profile.answer_coverage_ratio < 1.0:
        raise FingerprintChainError(
            f"profile answer coverage must be complete for {expected_model_id}"
        )
    if any(
        prompt.answer_coverage_ratio is not None and prompt.answer_coverage_ratio < 1.0
        for prompt in profile.prompts
    ):
        raise FingerprintChainError(
            f"profile prompt coverage must be complete for {expected_model_id}"
        )


def _validate_baseline_run(
    run: RunArtifact,
    expected_model_id: str,
    suite: SuiteDefinition,
) -> None:
    if run.run_kind != "full_suite":
        raise FingerprintChainError(
            f"baseline run must be full_suite for {expected_model_id}, got {run.run_kind}"
        )
    if run.suite_id != suite.id:
        raise FingerprintChainError(
            f"baseline run suite mismatch for {expected_model_id}: {run.suite_id} != {suite.id}"
        )
    if run.claimed_model != expected_model_id:
        raise FingerprintChainError(
            f"baseline run claimed_model mismatch: {run.claimed_model} != {expected_model_id}"
        )
    total_prompts = len(suite.prompt_ids)
    if run.prompt_count_total != total_prompts:
        raise FingerprintChainError(
            f"baseline run prompt_count_total mismatch for {expected_model_id}"
        )
    if run.prompt_count_completed != total_prompts:
        raise FingerprintChainError(
            f"baseline run is incomplete for {expected_model_id}"
        )
    if run.prompt_count_scoreable != total_prompts:
        raise FingerprintChainError(
            f"baseline run is not fully scoreable for {expected_model_id}"
        )
    prompt_ids = [prompt.prompt_id for prompt in run.prompts]
    if sorted(prompt_ids) != sorted(suite.prompt_ids):
        raise FingerprintChainError(
            f"baseline run prompt set mismatch for {expected_model_id}: {prompt_ids}"
        )


def _validate_pinned_file(path: Path, expected_sha256: str) -> None:
    if not path.exists():
        raise FingerprintChainError(f"missing pinned artifact: {path}")
    actual_sha256 = _sha256(path)
    if actual_sha256 != expected_sha256:
        raise FingerprintChainError(
            f"sha256 mismatch for {path}: {actual_sha256} != {expected_sha256}"
        )


def _resolve_repo_path(root: Path, relative_path: str) -> Path:
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise FingerprintChainError(f"manifest path escapes repository root: {relative_path}") from exc
    return path


def _profile_map(profiles: list[ProfileArtifact]) -> dict[str, ProfileArtifact]:
    return {profile.model_id: profile for profile in profiles}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
