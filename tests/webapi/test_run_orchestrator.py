from __future__ import annotations

import json
from pathlib import Path

from modelfingerprint.contracts.profile import (
    BooleanFeatureSummary,
    EnumFeatureSummary,
    NumericFeatureSummary,
    ProfileArtifact,
)
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.prompt_bank import load_suites
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.webapi.contracts import WebRunInput
from modelfingerprint.webapi.run_orchestrator import RunOrchestrator, WebRunConfigurationError
from modelfingerprint.webapi.run_store import RunStore

ROOT = Path(__file__).resolve().parents[2]


class RecordingRunStore(RunStore):
    def __init__(self, directory: Path) -> None:
        super().__init__(directory)
        self.history: list[tuple[str, str | None]] = []

    def create_run(self, **kwargs):
        record = super().create_run(**kwargs)
        self.history.append((record.run_status, record.result_state))
        return record

    def save(self, record):
        updated = super().save(record)
        self.history.append((updated.run_status, updated.result_state))
        return updated


def test_orchestrator_completes_v3_suite_and_writes_formal_result(tmp_path: Path) -> None:
    store = RecordingRunStore(tmp_path / ".webapi" / "runs")
    paths = RepositoryPaths(root=ROOT)
    input = WebRunInput(
        base_url="https://api.example.com/v1",
        model_name="gpt-4o-mini",
        fingerprint_model_id="glm-5",
    )

    orchestrator = RunOrchestrator(
        paths=paths,
        store=store,
        probe_capabilities_fn=lambda **_: {"results": {"thinking": {"status": "supported"}}},
        execute_suite_fn=lambda **_: _build_matching_v3_artifact(
            paths=paths,
            claimed_model=input.fingerprint_model_id,
            target_label="run_001",
        ),
    )

    record = orchestrator.run(run_id="run_001", input=input)

    assert store.history[0] == ("validating", None)
    assert ("running", None) in store.history
    assert record.run_status == "completed"
    assert record.result_state == "formal_result"
    assert record.result is not None
    assert record.result.verdict == "match"
    assert record.result.summary is not None
    assert record.result.summary.top_candidate_model_id == "glm-5"


def test_orchestrator_marks_configuration_error_when_probe_fails(tmp_path: Path) -> None:
    store = RecordingRunStore(tmp_path / ".webapi" / "runs")
    paths = RepositoryPaths(root=ROOT)
    input = WebRunInput(
        base_url="https://api.example.com/v1",
        model_name="gpt-4o-mini",
        fingerprint_model_id="glm-5",
    )

    orchestrator = RunOrchestrator(
        paths=paths,
        store=store,
        probe_capabilities_fn=lambda **_: _raise_configuration_error(),
        execute_suite_fn=lambda **_: None,
    )

    record = orchestrator.run(run_id="run_401", input=input)

    assert record.run_status == "configuration_error"
    assert record.result_state == "configuration_error"
    assert record.failure is not None
    assert record.failure.code == "AUTH_FAILED"


def test_orchestrator_marks_incompatible_protocol_when_run_artifact_requires_it(
    tmp_path: Path,
) -> None:
    store = RecordingRunStore(tmp_path / ".webapi" / "runs")
    paths = RepositoryPaths(root=ROOT)
    input = WebRunInput(
        base_url="https://api.example.com/v1",
        model_name="gpt-4o-mini",
        fingerprint_model_id="glm-5",
    )

    orchestrator = RunOrchestrator(
        paths=paths,
        store=store,
        probe_capabilities_fn=lambda **_: {"results": {"thinking": {"status": "supported"}}},
        execute_suite_fn=lambda **_: _build_matching_v3_artifact(
            paths=paths,
            claimed_model=input.fingerprint_model_id,
            target_label="run_402",
            protocol_satisfied=False,
        ),
    )

    record = orchestrator.run(run_id="run_402", input=input)

    assert record.run_status == "completed"
    assert record.result_state == "incompatible_protocol"
    assert record.result is not None
    assert record.result.diagnostics.protocol_status == "incompatible_protocol"


def _raise_configuration_error():
    raise WebRunConfigurationError(
        code="AUTH_FAILED",
        message="upstream returned 401",
        http_status=401,
    )


def _build_matching_v3_artifact(
    *,
    paths: RepositoryPaths,
    claimed_model: str,
    target_label: str,
    protocol_satisfied: bool = True,
) -> RunArtifact:
    suites = load_suites(paths.prompt_bank_dir / "suites")
    suite = suites["fingerprint-suite-v3"]
    profile = ProfileArtifact.model_validate(
        json.loads(
            (
                paths.profiles_dir / "fingerprint-suite-v3" / f"{claimed_model}.json"
            ).read_text()
        )
    )
    prompt_summaries = {prompt.prompt_id: prompt for prompt in profile.prompts}

    prompts = []
    for prompt_id in suite.prompt_ids:
        summary = prompt_summaries[prompt_id]
        prompts.append(
            {
                "prompt_id": prompt_id,
                "status": "completed",
                "raw_output": f"synthetic output for {prompt_id}",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 12,
                    "reasoning_tokens": 0,
                    "total_tokens": 22,
                },
                "features": {
                    feature_name: _representative_feature_value(feature_summary)
                    for feature_name, feature_summary in summary.features.items()
                },
            }
        )

    return RunArtifact.model_validate(
        {
            "run_id": f"{target_label}.fingerprint-suite-v3",
            "suite_id": "fingerprint-suite-v3",
            "target_label": target_label,
            "claimed_model": claimed_model,
            "prompt_count_total": len(prompts),
            "prompt_count_completed": len(prompts),
            "prompt_count_scoreable": len(prompts),
            "answer_coverage_ratio": 1.0,
            "reasoning_coverage_ratio": 1.0,
            "protocol_compatibility": {
                "satisfied": protocol_satisfied,
                "required_capabilities": ["chat_completions"],
                "issues": (
                    []
                    if protocol_satisfied
                    else ["run contains unsupported capability prompts"]
                ),
            },
            "prompts": prompts,
        }
    )


def _representative_feature_value(
    summary: NumericFeatureSummary | BooleanFeatureSummary | EnumFeatureSummary,
):
    if isinstance(summary, NumericFeatureSummary):
        return summary.median
    if isinstance(summary, BooleanFeatureSummary):
        return summary.p_true >= 0.5
    return max(summary.distribution.items(), key=lambda item: item[1])[0]
