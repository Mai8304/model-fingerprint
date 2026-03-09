from __future__ import annotations

import json
import shutil
from datetime import date
from pathlib import Path

from modelfingerprint.adapters.openai_chat import ChatCompletionResult
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.suite_runner import SuiteRunner
from modelfingerprint.settings import RepositoryPaths


ROOT = Path(__file__).resolve().parents[2]


class FakeTransport:
    def complete(self, prompt: PromptDefinition) -> ChatCompletionResult:
        payloads = {
            "p001": "Use CRUD first. Event sourcing adds overhead.",
            "p003": '{"answer":"yes","confidence":"high"}',
            "p005": '@@ -1 +1 @@\n-print("old")\n+print("new")',
            "p007": '{"requested_fields":["name","role"],"extracted":{"name":"Alice","role":"admin"},"evidence":["name","role"],"hallucinated":[]}',
            "p009": '{"expected_needles":["alpha","beta","gamma"],"found_needles":["gamma","delta","alpha"]}',
        }
        return ChatCompletionResult(
            content=payloads[prompt.id],
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
        )


def test_suite_runner_executes_screening_suite_and_writes_run(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", tmp_path / "prompt-bank")
    shutil.copytree(ROOT / "extractors", tmp_path / "extractors")

    runner = SuiteRunner(
        paths=RepositoryPaths(root=tmp_path),
        transport=FakeTransport(),
    )

    output_path = runner.run_suite(
        suite_id="screening-v1",
        target_label="suspect-a",
        claimed_model="gpt-5.3",
        run_date=date(2026, 3, 9),
    )

    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    assert output_path == tmp_path / "runs" / "2026-03-09" / "suspect-a.screening-v1.json"
    assert artifact.suite_id == "screening-v1"
    assert len(artifact.prompts) == 5
    assert all(prompt.raw_output for prompt in artifact.prompts)
    assert all(prompt.usage.total_tokens == 15 for prompt in artifact.prompts)
    assert all(prompt.features for prompt in artifact.prompts)
