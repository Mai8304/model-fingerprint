from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.run import (
    PromptExecutionError,
    RunArtifact,
    UsageMetadata,
)
from modelfingerprint.services.feature_pipeline import PromptExecutionResult

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def write_v3_fixture_responses(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "p021": {
                    "content": (
                        '结果如下：\n```json\n'
                        '{"result":{"owner":"Alice Wong","role":"Primary DBA","region":null,'
                        '"change_window":"2026-03-21 02:00 UTC"},'
                        '"evidence_map":{"owner":["e3"],"role":["e2"],"region":[],"change_window":["e5"]},'
                        '"unknown_fields":{"region":"missing"},"violations":[]}\n```\n谢谢'
                    ),
                    "reasoning_content": "1. ignore draft facts\n2. keep region unknown",
                    "input_tokens": 20,
                    "output_tokens": 30,
                    "reasoning_tokens": 18,
                    "total_tokens": 68,
                    "finish_reason": "stop",
                },
                "p023": {
                    "content": (
                        '{"task_result":{"q1":{"status":"answer","value":"yes"},'
                        '"q2":{"status":"unknown","value":null},'
                        '"q3":{"status":"answer","value":"retry failed background jobs"},'
                        '"q4":{"status":"conflict_unresolved","value":null}},'
                        '"evidence":{"q1":["e1"],"q2":["e5"],"q3":["e1"],"q4":["e3","e4"]},'
                        '"unknowns":{"q2":"missing_actor","q4":"conflicting_notes"},"violations":[]}'
                    ),
                    "reasoning_content": (
                        "1. split answerable from unresolved\n2. keep q4 conflicted"
                    ),
                    "input_tokens": 24,
                    "output_tokens": 28,
                    "reasoning_tokens": 21,
                    "total_tokens": 73,
                    "finish_reason": "stop",
                },
                "p024": {
                    "content": (
                        'Final JSON: '
                        '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
                        '"ticket_b":{"status":"open","owner":"db","priority":"p2"},'
                        '"worker_x":{"status":"suspended","owner":"ml","priority":"p3"}},'
                        '"evidence":{"derivation_codes":{"ticket_a":"r5","ticket_b":"r6","worker_x":"r10"},'
                        '"defaults_used":["ticket_b.priority"]},"unknowns":{},"violations":[]}'
                    ),
                    "reasoning_content": (
                        "1. apply close/reopen rules\n2. preserve owner on suspend"
                    ),
                    "input_tokens": 30,
                    "output_tokens": 32,
                    "reasoning_tokens": 25,
                    "total_tokens": 87,
                    "finish_reason": "stop",
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def test_run_suite_command_executes_fixture_mode_and_writes_v3_run(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")
    fixture_path = tmp_path / "v3-responses.json"
    write_v3_fixture_responses(fixture_path)

    result = runner.invoke(
        app,
        [
            "run-suite",
            "quick-check-v3",
            "--root",
            str(tmp_path),
            "--target-label",
            "suspect-v3",
            "--claimed-model",
            "glm-5",
            "--fixture-responses",
            str(fixture_path),
            "--run-date",
            "2026-03-10",
        ],
    )

    assert result.exit_code == 0

    output_path = tmp_path / "runs" / "2026-03-10" / "suspect-v3.quick-check-v3.json"
    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    assert artifact.suite_id == "quick-check-v3"
    assert artifact.prompt_count_total == 3
    assert artifact.prompt_count_completed == 3
    assert artifact.prompt_count_scoreable == 3
    assert artifact.answer_coverage_ratio == 1.0
    assert artifact.reasoning_coverage_ratio == 1.0
    assert artifact.capability_probe is None
    assert artifact.protocol_compatibility is not None
    assert artifact.protocol_compatibility.satisfied is True
    assert all(prompt.canonical_output is not None for prompt in artifact.prompts)


class FlakyTransport:
    def __init__(self) -> None:
        self.called_prompt_ids: list[str] = []

    def execute(self, prompt) -> PromptExecutionResult:
        self.called_prompt_ids.append(prompt.id)
        if prompt.id == "p021":
            raise RuntimeError("socket exploded")
        payloads = {
            "p023": (
                '{"task_result":{"q1":{"status":"answer","value":"yes"},'
                '"q2":{"status":"unknown","value":null},'
                '"q3":{"status":"answer","value":"retry failed background jobs"},'
                '"q4":{"status":"conflict_unresolved","value":null}},'
                '"evidence":{"q1":["e1"],"q2":["e5"],"q3":["e1"],"q4":["e3","e4"]},'
                '"unknowns":{"q2":"missing_actor","q4":"conflicting_notes"},"violations":[]}'
            ),
            "p024": (
                '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
                '"ticket_b":{"status":"open","owner":"db","priority":"p2"},'
                '"worker_x":{"status":"suspended","owner":"ml","priority":"p3"}},'
                '"evidence":{"derivation_codes":{"ticket_a":"r5","ticket_b":"r6","worker_x":"r10"},'
                '"defaults_used":["ticket_b.priority"]},"unknowns":{},"violations":[]}'
            ),
        }
        return PromptExecutionResult(
            prompt=prompt,
            raw_output=payloads[prompt.id],
            usage=UsageMetadata(input_tokens=10, output_tokens=5, total_tokens=15),
        )


def test_suite_runner_keeps_running_when_one_prompt_transport_raises(tmp_path: Path) -> None:
    from modelfingerprint.services.suite_runner import SuiteRunner
    from modelfingerprint.settings import RepositoryPaths

    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")

    transport = FlakyTransport()
    runner_instance = SuiteRunner(paths=RepositoryPaths(root=tmp_path), transport=transport)

    output_path = runner_instance.run_suite(
        suite_id="quick-check-v3",
        target_label="suspect-b",
        claimed_model=None,
    )

    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    assert transport.called_prompt_ids == ["p021", "p023", "p024"]
    prompt_statuses = {prompt.prompt_id: prompt.status for prompt in artifact.prompts}
    assert prompt_statuses["p021"] == "transport_error"
    assert prompt_statuses["p023"] == "completed"
    assert prompt_statuses["p024"] == "completed"
    first_prompt = next(prompt for prompt in artifact.prompts if prompt.prompt_id == "p021")
    assert first_prompt.error == PromptExecutionError(
        kind="unexpected_transport_runtime_error",
        message="socket exploded",
        retryable=False,
        http_status=None,
    )


def test_normalize_capability_probe_payload_accepts_extended_image_keys() -> None:
    from modelfingerprint.services.suite_runner import _normalize_capability_probe_payload

    normalized = _normalize_capability_probe_payload(
        {
            "probe_mode": "minimal",
            "probe_version": "v1",
            "coverage_ratio": 1.0,
            "results": {
                "thinking": {"status": "supported"},
                "image_generation": {"status": "unsupported"},
                "vision_understanding": {"status": "unsupported"},
            },
        }
    )

    assert normalized is not None
    assert normalized.capabilities["thinking"].status == "supported"
    assert normalized.capabilities["image_generation"].status == "unsupported"
    assert normalized.capabilities["vision_understanding"].status == "unsupported"
