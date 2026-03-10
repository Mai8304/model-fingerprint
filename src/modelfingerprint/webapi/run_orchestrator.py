from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.services.capability_probe import probe_capabilities
from modelfingerprint.services.comparison_artifact import build_comparison_artifact
from modelfingerprint.services.prompt_bank import load_suites
from modelfingerprint.services.runtime_policy import resolve_runtime_policy
from modelfingerprint.services.suite_runner import SuiteRunner
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.transports.live_runner import LiveRunner
from modelfingerprint.webapi.contracts import (
    WebResultState,
    WebRunFailure,
    WebRunInput,
    WebRunPrompt,
    WebRunRecord,
    WebRunResult,
    WebRunResultCandidate,
    WebRunResultDiagnostics,
    WebRunResultFingerprint,
    WebRunResultSummary,
)
from modelfingerprint.webapi.fingerprints import (
    WEB_FINGERPRINT_SUITE_ID,
    display_model_label,
)
from modelfingerprint.webapi.run_store import RunStore

ProbeCapabilitiesFn = Callable[..., dict[str, object]]
ExecuteSuiteFn = Callable[..., RunArtifact]


@dataclass(frozen=True)
class WebRunConfigurationError(RuntimeError):
    code: str
    message: str
    http_status: int | None = None
    retryable: bool | None = None

    def __str__(self) -> str:
        return self.message


class RunOrchestrator:
    def __init__(
        self,
        *,
        paths: RepositoryPaths,
        store: RunStore,
        probe_capabilities_fn: ProbeCapabilitiesFn | None = None,
        execute_suite_fn: ExecuteSuiteFn | None = None,
    ) -> None:
        self._paths = paths
        self._store = store
        self._probe_capabilities_fn = probe_capabilities_fn or probe_capabilities
        self._execute_suite_fn = execute_suite_fn or self._execute_suite

    def run(self, *, run_id: str, input: WebRunInput) -> WebRunRecord:
        return self.run_with_api_key(run_id=run_id, input=input, api_key="inline")

    def initialize_run(self, *, run_id: str, input: WebRunInput) -> WebRunRecord:
        suite = self._load_web_suite()
        self._ensure_selected_fingerprint_exists(input.fingerprint_model_id)
        return self._store.create_run(
            run_id=run_id,
            input=input,
            prompt_ids=list(suite.prompt_ids),
        )

    def run_with_api_key(
        self,
        *,
        run_id: str,
        input: WebRunInput,
        api_key: str,
    ) -> WebRunRecord:
        suite = self._load_web_suite()
        self._ensure_selected_fingerprint_exists(input.fingerprint_model_id)
        record = self._load_or_create_record(
            run_id=run_id,
            input=input,
            prompt_ids=list(suite.prompt_ids),
        )
        if record.cancel_requested:
            return self._save_stopped_record(record)

        try:
            capability_probe_payload = self._probe_capabilities_fn(
                base_url=input.base_url,
                api_key=api_key,
                model=input.model_name,
            )
        except WebRunConfigurationError as exc:
            return self._store.save(
                record.model_copy(
                    update={
                        "run_status": "configuration_error",
                        "result_state": "configuration_error",
                        "failure": self._build_failure(exc),
                    }
                )
            )

        record = self._store.save(record.model_copy(update={"run_status": "running"}))
        if self._store.get(run_id).cancel_requested:
            return self._save_stopped_record(record)

        artifact = self._execute_suite_fn(
            run_id=run_id,
            input=input,
            api_key=api_key,
            capability_probe_payload=capability_probe_payload,
        )
        prompt_items = [_project_prompt(prompt) for prompt in artifact.prompts]
        if self._store.get(run_id).cancel_requested:
            return self._save_stopped_record(record, prompts=prompt_items)
        result_state = _determine_result_state(artifact)
        result = self._build_result(
            run_artifact=artifact,
            input=input,
            result_state=result_state,
        )

        return self._store.save(
            record.model_copy(
                update={
                    "run_status": "completed",
                    "result_state": result_state,
                    "prompts": prompt_items,
                    "eta_seconds": 0,
                    "failure": None,
                    "result": result,
                }
            )
        )

    def _build_result(
        self,
        *,
        run_artifact: RunArtifact,
        input: WebRunInput,
        result_state: WebResultState,
    ) -> WebRunResult:
        profiles = self._load_profiles(run_artifact.suite_id)
        calibration = self._load_calibration(run_artifact.suite_id)
        comparison = build_comparison_artifact(
            run=run_artifact,
            profiles=profiles,
            calibration=calibration,
        )
        selected_candidate = next(
            (
                candidate
                for candidate in comparison.candidates
                if candidate.model_id == input.fingerprint_model_id
            ),
            None,
        )

        return WebRunResult(
            run_id=run_artifact.run_id,
            result_state=result_state,
            selected_fingerprint=WebRunResultFingerprint(
                id=input.fingerprint_model_id,
                label=display_model_label(input.fingerprint_model_id),
            ),
            completed_prompts=run_artifact.prompt_count_completed or 0,
            total_prompts=run_artifact.prompt_count_total or len(run_artifact.prompts),
            verdict=comparison.summary.verdict,
            summary=WebRunResultSummary(
                similarity_score=(
                    None
                    if selected_candidate is None
                    else selected_candidate.overall_similarity
                ),
                top_candidate_model_id=comparison.summary.top1_model,
                top_candidate_label=display_model_label(comparison.summary.top1_model),
            ),
            candidates=[
                WebRunResultCandidate(
                    model_id=candidate.model_id,
                    label=display_model_label(candidate.model_id),
                    similarity=candidate.overall_similarity,
                )
                for candidate in comparison.candidates
            ],
            diagnostics=WebRunResultDiagnostics(
                protocol_status=comparison.coverage.protocol_status,
                protocol_issues=list(comparison.diagnostics.protocol_issues),
                hard_mismatches=list(comparison.diagnostics.hard_mismatches),
            ),
        )

    def _execute_suite(
        self,
        *,
        run_id: str,
        input: WebRunInput,
        api_key: str,
        capability_probe_payload: dict[str, object],
    ) -> RunArtifact:
        endpoint = _build_inline_endpoint_profile(
            run_id=run_id,
            input=input,
            capability_probe_payload=capability_probe_payload,
        )
        runtime_policy = resolve_runtime_policy(
            capability_probe_payload=capability_probe_payload,
            supports_output_token_cap=endpoint.capabilities.supports_output_token_cap,
        )
        run_date = date.today()
        trace_dir = (
            self._paths.traces_dir
            / run_date.isoformat()
            / f"{run_id}.{WEB_FINGERPRINT_SUITE_ID}"
        )
        runner = SuiteRunner(
            self._paths,
            transport=LiveRunner(
                endpoint=endpoint,
                api_key=api_key,
                dialect=OpenAIChatDialectAdapter(),
                trace_dir=trace_dir,
                runtime_policy=runtime_policy,
            ),
        )
        output_path = runner.run_suite(
            suite_id=WEB_FINGERPRINT_SUITE_ID,
            target_label=run_id,
            claimed_model=input.fingerprint_model_id,
            run_date=run_date,
            capability_probe_payload=capability_probe_payload,
        )
        return RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    def _ensure_selected_fingerprint_exists(self, model_id: str) -> None:
        profile_path = self._paths.profiles_dir / WEB_FINGERPRINT_SUITE_ID / f"{model_id}.json"
        if not profile_path.exists():
            raise WebRunConfigurationError(
                code="UNKNOWN_FINGERPRINT_MODEL",
                message=f"unknown fingerprint model: {model_id}",
            )

    def _load_web_suite(self):
        suites = load_suites(self._paths.prompt_bank_dir / "suites")
        return suites[WEB_FINGERPRINT_SUITE_ID]

    def _load_profiles(self, suite_id: str) -> list[ProfileArtifact]:
        profile_dir = self._paths.profiles_dir / suite_id
        return [
            ProfileArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(profile_dir.glob("*.json"))
        ]

    def _load_calibration(self, suite_id: str) -> CalibrationArtifact:
        path = self._paths.calibration_dir / f"{suite_id}.json"
        return CalibrationArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def _build_failure(self, exc: WebRunConfigurationError) -> WebRunFailure:
        return WebRunFailure(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            http_status=exc.http_status,
        )

    def _load_or_create_record(
        self,
        *,
        run_id: str,
        input: WebRunInput,
        prompt_ids: list[str],
    ) -> WebRunRecord:
        try:
            return self._store.get(run_id)
        except FileNotFoundError:
            return self._store.create_run(
                run_id=run_id,
                input=input,
                prompt_ids=prompt_ids,
            )

    def _save_stopped_record(
        self,
        record: WebRunRecord,
        *,
        prompts: list[WebRunPrompt] | None = None,
    ) -> WebRunRecord:
        return self._store.save(
            record.model_copy(
                update={
                    "run_status": "stopped",
                    "result_state": "stopped",
                    "prompts": record.prompts if prompts is None else prompts,
                    "failure": WebRunFailure(
                        code="RUN_STOPPED",
                        message="run was stopped before completion",
                        retryable=False,
                    ),
                    "result": None,
                }
            )
        )


def _project_prompt(prompt) -> WebRunPrompt:
    status = "completed" if prompt.status == "completed" else "failed"
    error = prompt.error
    return WebRunPrompt(
        prompt_id=prompt.prompt_id,
        status=status,
        elapsed_seconds=None if prompt.completion is None else prompt.completion.latency_ms // 1000,
        summary_code=_summary_code_for_prompt(prompt.status),
        error_code=_error_code_for_prompt(prompt.status),
        error_detail=None if error is None else error.message,
        http_status=None if error is None else error.http_status,
    )


def _summary_code_for_prompt(status: str) -> str:
    if status == "completed":
        return "FEATURES_EXTRACTED"
    if status == "unsupported_capability":
        return "PROTOCOL_CHECKED"
    return "WAITING_FOR_RESPONSE"


def _error_code_for_prompt(status: str) -> str | None:
    return {
        "timeout": "RESPONSE_TIMEOUT",
        "transport_error": "TRANSPORT_ERROR",
        "unsupported_capability": "UNSUPPORTED_CAPABILITY",
        "truncated": "TRUNCATED_RESPONSE",
        "invalid_response": "UNPARSEABLE_RESPONSE",
        "canonicalization_error": "CANONICALIZATION_ERROR",
    }.get(status)


def _determine_result_state(run_artifact: RunArtifact) -> WebResultState:
    compatibility = run_artifact.protocol_compatibility
    if compatibility is not None and not compatibility.satisfied:
        return "incompatible_protocol"

    scoreable = run_artifact.prompt_count_scoreable or 0
    total = run_artifact.prompt_count_total or len(run_artifact.prompts)
    completed = run_artifact.prompt_count_completed or 0
    if scoreable >= total and completed >= total:
        return "formal_result"
    if scoreable >= 3:
        return "provisional"
    return "insufficient_evidence"


def _build_inline_endpoint_profile(
    *,
    run_id: str,
    input: WebRunInput,
    capability_probe_payload: dict[str, object],
) -> EndpointProfile:
    thinking_outcome = capability_probe_payload.get("results", {})
    exposes_reasoning_text = False
    if isinstance(thinking_outcome, dict):
        thinking = thinking_outcome.get("thinking")
        if isinstance(thinking, dict):
            exposes_reasoning_text = thinking.get("status") == "supported"

    return EndpointProfile.model_validate(
        {
            "id": f"web-run-{run_id}",
            "dialect": "openai_chat_v1",
            "base_url": input.base_url,
            "model": input.model_name,
            "auth": {
                "kind": "bearer_env",
                "env_var": "MODEL_FINGERPRINT_API_KEY",
            },
            "capabilities": {
                "exposes_reasoning_text": exposes_reasoning_text,
                "supports_json_object_response": False,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_output_token_cap": True,
            },
            "request_mapping": {
                "output_token_cap_field": "max_tokens",
                "static_body": {},
            },
            "response_mapping": {
                "answer_text_path": "choices.0.message.content",
                "reasoning_text_path": (
                    "choices.0.message.reasoning_content" if exposes_reasoning_text else None
                ),
                "finish_reason_path": "choices.0.finish_reason",
                "usage_paths": {
                    "prompt_tokens": "usage.prompt_tokens",
                    "output_tokens": "usage.completion_tokens",
                    "total_tokens": "usage.total_tokens",
                    "reasoning_tokens": "usage.completion_tokens_details.reasoning_tokens",
                },
            },
            "timeout_policy": {
                "connect_seconds": 10,
                "read_seconds": 120,
            },
            "retry_policy": {
                "max_attempts": 1,
                "retryable_statuses": [408, 429, 500, 502, 503, 504],
            },
        }
    )
