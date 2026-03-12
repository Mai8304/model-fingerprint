from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from modelfingerprint.cli import app
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.prompt_bank import load_candidate_prompts
from modelfingerprint.transports.http_client import HttpProgressSnapshot, HttpTerminalResult

ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


@dataclass(frozen=True)
class LiveSmokeBaseline:
    endpoint_profile_id: str
    protocol_family: str
    provider_id: str | None
    model: str
    request_prompt_id: str
    reasoning_field: str
    expected_request_headers: dict[str, str]
    expected_request_body_subset: dict[str, object]
    forbidden_request_body_keys: tuple[str, ...]
    direct_latency_ms: int


LIVE_SMOKE_BASELINES: dict[str, LiveSmokeBaseline] = {
    "openrouter-glm-5": LiveSmokeBaseline(
        endpoint_profile_id="openrouter-glm-5",
        protocol_family="openai_compatible",
        provider_id=None,
        model="z-ai/glm-5",
        request_prompt_id="p021",
        reasoning_field="reasoning",
        expected_request_headers={
            "Accept": "application/json",
            "HTTP-Referer": "https://codex.local",
            "X-Title": "Codex Model Fingerprint",
        },
        expected_request_body_subset={
            "model": "z-ai/glm-5",
            "reasoning": {"effort": "minimal", "exclude": False},
        },
        forbidden_request_body_keys=(),
        direct_latency_ms=3210,
    ),
    "moonshot-kimi-k2.5": LiveSmokeBaseline(
        endpoint_profile_id="moonshot-kimi-k2.5",
        protocol_family="openai_compatible",
        provider_id="moonshot",
        model="kimi-k2.5",
        request_prompt_id="p021",
        reasoning_field="reasoning_content",
        expected_request_headers={
            "Accept": "application/json",
        },
        expected_request_body_subset={
            "model": "kimi-k2.5",
        },
        forbidden_request_body_keys=("temperature", "top_p"),
        direct_latency_ms=2875,
    ),
}


class FakeInFlightHandle:
    def __init__(self, payload: dict[str, object], latency_ms: int) -> None:
        self._terminal = HttpTerminalResult(payload=payload, latency_ms=latency_ms, error=None)

    def snapshot(self) -> HttpProgressSnapshot:
        return HttpProgressSnapshot(
            bytes_received=128,
            has_any_data=True,
            elapsed_ms=50,
            first_byte_latency_ms=50,
            last_progress_latency_ms=50,
            completed=True,
        )

    def wait_until_terminal(
        self,
        timeout_seconds: float | None = None,
    ) -> HttpTerminalResult | None:
        return self._terminal

    def cancel(self) -> None:
        return None


def _copy_repo_inputs(root: Path) -> None:
    shutil.copytree(ROOT / "prompt-bank", root / "prompt-bank")
    shutil.copytree(ROOT / "extractors", root / "extractors")
    shutil.copytree(ROOT / "endpoint-profiles", root / "endpoint-profiles")


def _baseline_payload(case: LiveSmokeBaseline, request_body: dict[str, object]) -> dict[str, object]:
    user_message = request_body["messages"][-1]["content"]
    if "ticket_a" in user_message:
        answer_text = (
            '{"task_result":{"ticket_a":{"status":"closed","owner":"ops","priority":"p1"},'
            '"ticket_b":{"status":"open","owner":"db","priority":"p2"},'
            '"worker_x":{"status":"suspended","owner":"ml","priority":"p3"}},'
            '"evidence":{"derivation_codes":{"ticket_a":"r5","ticket_b":"r6","worker_x":"r10"},'
            '"defaults_used":["ticket_b.priority"]},"unknowns":{},"violations":[]}'
        )
        reasoning_text = "1. apply close and reopen rules\n2. preserve owner on suspend"
    elif "q1" in user_message:
        answer_text = (
            '{"task_result":{"q1":{"status":"answer","value":"yes"},'
            '"q2":{"status":"unknown","value":null},'
            '"q3":{"status":"answer","value":"retry failed background jobs"},'
            '"q4":{"status":"conflict_unresolved","value":null}},'
            '"evidence":{"q1":["e1"],"q2":["e5"],"q3":["e1"],"q4":["e3","e4"]},'
            '"unknowns":{"q2":"missing_actor","q4":"conflicting_notes"},"violations":[]}'
        )
        reasoning_text = "1. separate answers from unknowns\n2. keep q4 unresolved"
    else:
        answer_text = (
            '{"task_result":{"owner":"Alice Wong","role":"Primary DBA","region":null,'
            '"change_window":"2026-03-21 02:00 UTC"},'
            '"evidence":{"owner":["e3"],"role":["e2"],"region":[],"change_window":["e5"]},'
            '"unknowns":{"region":"missing"},"violations":[]}'
        )
        reasoning_text = "1. prefer approved facts\n2. keep region unknown"
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": answer_text,
                    case.reasoning_field: reasoning_text,
                },
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 21,
            "completion_tokens_details": {"reasoning_tokens": 6},
        },
    }


def _build_probe_payload(case: LiveSmokeBaseline, *, base_url: str, model: str) -> dict[str, object]:
    return {
        "base_url": base_url,
        "model": model,
        "probe_mode": "minimal",
        "probe_version": "v2",
        "coverage_ratio": 0.8,
        "results": {
            "thinking": {
                "capability": "thinking",
                "status": "supported",
                "detail": f"{case.endpoint_profile_id} reasoning visible",
                "evidence": {"field": case.reasoning_field},
                "http_status": 200,
                "latency_ms": 1000,
            },
            "tools": {
                "capability": "tools",
                "status": "supported",
                "detail": "tool baseline",
                "evidence": {},
                "http_status": 200,
                "latency_ms": 800,
            },
            "streaming": {
                "capability": "streaming",
                "status": "supported",
                "detail": "sse",
                "evidence": {"content_type": "text/event-stream"},
                "http_status": 200,
                "latency_ms": 700,
            },
            "image": {
                "capability": "image",
                "status": "unsupported",
                "detail": "not in smoke baseline",
                "evidence": {},
                "http_status": 404,
                "latency_ms": 600,
            },
        },
    }


def _assert_mapping_contains_subset(actual: dict[str, object], expected_subset: dict[str, object]) -> None:
    for key, expected_value in expected_subset.items():
        assert key in actual
        actual_value = actual[key]
        if isinstance(expected_value, dict):
            assert isinstance(actual_value, dict)
            _assert_mapping_contains_subset(actual_value, expected_value)
            continue
        assert actual_value == expected_value


@pytest.mark.parametrize(
    "endpoint_profile_id",
    ["openrouter-glm-5", "moonshot-kimi-k2.5"],
)
def test_run_suite_live_smoke_matches_direct_protocol_baseline(
    tmp_path: Path,
    monkeypatch,
    endpoint_profile_id: str,
) -> None:
    _copy_repo_inputs(tmp_path)
    monkeypatch.setenv("MODEL_FINGERPRINT_API_KEY", "secret-key")
    baseline = LIVE_SMOKE_BASELINES[endpoint_profile_id]

    def fake_start(self, request, *, connect_timeout_seconds: int, read_timeout_seconds: int):
        return FakeInFlightHandle(
            _baseline_payload(baseline, request.body),
            latency_ms=baseline.direct_latency_ms,
        )

    def fake_probe_capabilities(*, base_url: str, api_key: str, model: str):
        assert api_key == "secret-key"
        return _build_probe_payload(baseline, base_url=base_url, model=model)

    monkeypatch.setattr(
        "modelfingerprint.transports.http_client.StandardHttpClient.start",
        fake_start,
    )
    monkeypatch.setattr(
        "modelfingerprint.cli.probe_capabilities",
        fake_probe_capabilities,
    )

    result = runner.invoke(
        app,
        [
            "run-suite",
            "quick-check-v3",
            "--root",
            str(tmp_path),
            "--target-label",
            f"smoke-{endpoint_profile_id}",
            "--endpoint-profile",
            endpoint_profile_id,
            "--run-date",
            "2026-03-12",
        ],
    )

    assert result.exit_code == 0

    output_path = (
        tmp_path
        / "runs"
        / "2026-03-12"
        / f"smoke-{endpoint_profile_id}.quick-check-v3.json"
    )
    artifact = RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))
    trace_dir = tmp_path / "traces" / "2026-03-12" / f"smoke-{endpoint_profile_id}.quick-check-v3"
    request_trace = json.loads(
        (trace_dir / f"{baseline.request_prompt_id}.request.json").read_text(encoding="utf-8")
    )
    response_trace = json.loads(
        (trace_dir / f"{baseline.request_prompt_id}.response.json").read_text(encoding="utf-8")
    )
    prompt_bank = load_candidate_prompts(tmp_path / "prompt-bank" / "candidates")
    prompt = prompt_bank[baseline.request_prompt_id]

    assert artifact.endpoint_profile_id == baseline.endpoint_profile_id
    assert artifact.capability_probe is not None
    assert artifact.capability_probe.probe_version == "v2"
    assert artifact.prompt_count_completed == 3
    assert all(prompt.status == "completed" for prompt in artifact.prompts)
    assert all(len(prompt.attempts) == 1 for prompt in artifact.prompts)
    assert all(prompt.attempts[0].latency_ms == baseline.direct_latency_ms for prompt in artifact.prompts)

    assert request_trace["url"].endswith("/chat/completions")
    assert request_trace["headers"]["Authorization"] == "Bearer ***REDACTED***"
    _assert_mapping_contains_subset(request_trace["headers"], baseline.expected_request_headers)
    _assert_mapping_contains_subset(request_trace["body"], baseline.expected_request_body_subset)
    assert request_trace["body"]["max_tokens"] == prompt.generation.max_output_tokens
    for forbidden_key in baseline.forbidden_request_body_keys:
        assert forbidden_key not in request_trace["body"]

    assert set(response_trace) == {"choices", "usage"}
    assert len(response_trace["choices"]) == 1
    assert set(response_trace["choices"][0]) == {"finish_reason", "message"}
    assert set(response_trace["choices"][0]["message"]) == {"content", baseline.reasoning_field}


@pytest.mark.skip(reason="pending anthropic_messages live smoke baseline")
def test_live_smoke_baseline_placeholder_for_anthropic_messages() -> None:
    pass


@pytest.mark.skip(reason="pending gemini_generate_content live smoke baseline")
def test_live_smoke_baseline_placeholder_for_gemini_generate_content() -> None:
    pass
