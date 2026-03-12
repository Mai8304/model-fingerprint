from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.dialects.base import build_protocol_family_adapter
from modelfingerprint.services.capability_probe import probe_capabilities
from modelfingerprint.services.comparison_artifact import build_comparison_artifact
from modelfingerprint.services.endpoint_profiles import (
    EndpointProfileResolutionError,
    load_endpoint_profiles,
    resolve_or_build_endpoint_profile,
)
from modelfingerprint.services.feature_pipeline import PromptExecutionResult
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
    WebRunResultCoverage,
    WebRunResultDiagnostics,
    WebRunResultDimensions,
    WebRunResultFingerprint,
    WebRunResultPromptBreakdown,
    WebRunResultSummary,
    WebRunResultThresholds,
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
    field: str | None = None

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
            self._set_stage(
                run_id,
                "config_validation",
                "completed",
                message="input accepted and worker execution started",
            )
            self._set_stage(
                run_id,
                "endpoint_resolution",
                "running",
                message="resolving endpoint configuration",
            )
            endpoint = self._resolve_input_endpoint_profile(input)
            self._set_stage(
                run_id,
                "endpoint_resolution",
                "completed",
                message=f"resolved endpoint profile: {endpoint.id}",
            )
            self._set_stage(
                run_id,
                "capability_probe",
                "running",
                message="probing endpoint capabilities",
            )
        except WebRunConfigurationError as exc:
            return self._save_configuration_error(run_id, exc, stage_id="endpoint_resolution")

        try:
            capability_probe_payload = self._probe_capabilities_fn(
                base_url=str(endpoint.base_url),
                api_key=api_key,
                model=endpoint.model,
            )
            self._raise_on_probe_configuration_failure(capability_probe_payload)
            self._set_stage(
                run_id,
                "capability_probe",
                "completed",
                message=_probe_summary_message(capability_probe_payload),
                run_status="running",
            )
            self._set_stage(
                run_id,
                "prompt_execution",
                "running",
                message="waiting to start prompt execution",
                run_status="running",
            )
        except WebRunConfigurationError as exc:
            return self._save_configuration_error(run_id, exc, stage_id="capability_probe")

        record = self._store.get(run_id)
        if self._store.get(run_id).cancel_requested:
            return self._save_stopped_record(record)

        artifact = self._execute_suite_fn(
            run_id=run_id,
            input=input,
            api_key=api_key,
            endpoint=endpoint,
            capability_probe_payload=capability_probe_payload,
            progress_callback=self._suite_progress_callback(run_id),
        )
        prompt_items = [_project_prompt(prompt) for prompt in artifact.prompts]
        if self._store.get(run_id).cancel_requested:
            return self._save_stopped_record(record, prompts=prompt_items)
        merged_record = self._store.update(
            run_id,
            lambda current, _: current.model_copy(
                update={
                    "prompts": _merge_prompt_metadata(current.prompts, prompt_items),
                    "eta_seconds": 0,
                }
            ),
        )
        prompt_items = merged_record.prompts
        self._set_stage(
            run_id,
            "prompt_execution",
            "completed",
            message=(
                "finished "
                f"{artifact.prompt_count_completed or 0} of "
                f"{artifact.prompt_count_total or len(artifact.prompts)} prompts"
            ),
            run_status="running",
        )
        self._set_stage(
            run_id,
            "comparison",
            "running",
            message="building comparison diagnostics",
            run_status="running",
        )
        result_state = _determine_result_state(artifact)
        result = self._build_result(
            run_artifact=artifact,
            input=input,
            result_state=result_state,
        )

        return self._store.update(
            run_id,
            lambda record, timestamp: record.model_copy(
                update={
                    "run_status": "completed",
                    "result_state": result_state,
                    "prompts": prompt_items,
                    "current_stage_id": "comparison",
                    "current_stage_message": "comparison diagnostics ready",
                    "stages": _update_stage_collection(
                        record.stages,
                        stage_id="comparison",
                        status="completed",
                        message="comparison diagnostics ready",
                        timestamp=timestamp,
                    ),
                    "eta_seconds": 0,
                    "failure": None,
                    "result": result,
                }
            ),
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
        top_candidate = comparison.candidates[0]
        selected_rank = next(
            (
                index
                for index, candidate in enumerate(comparison.candidates, start=1)
                if candidate.model_id == input.fingerprint_model_id
            ),
            None,
        )
        selected_candidate = next(
            (
                candidate
                for candidate in comparison.candidates
                if candidate.model_id == input.fingerprint_model_id
            ),
            None,
        )
        blocking_reasons = _build_blocking_reasons(comparison)

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
                top_candidate_similarity=comparison.summary.top1_similarity,
                top2_candidate_model_id=comparison.summary.top2_model,
                top2_candidate_label=display_model_label(comparison.summary.top2_model),
                top2_candidate_similarity=comparison.summary.top2_similarity,
                margin=comparison.summary.margin,
                consistency=comparison.summary.consistency,
            ),
            selected_candidate=(
                None
                if selected_candidate is None
                else WebRunResultCandidate(
                    model_id=selected_candidate.model_id,
                    label=display_model_label(selected_candidate.model_id),
                    similarity=selected_candidate.overall_similarity,
                    content_similarity=selected_candidate.content_similarity,
                    capability_similarity=selected_candidate.capability_similarity,
                    consistency=selected_candidate.consistency,
                    answer_coverage_ratio=selected_candidate.answer_coverage_ratio,
                    reasoning_coverage_ratio=selected_candidate.reasoning_coverage_ratio,
                    capability_coverage_ratio=selected_candidate.capability_coverage_ratio,
                    protocol_status=selected_candidate.protocol_status,
                    protocol_issues=list(selected_candidate.protocol_issues),
                    hard_mismatches=list(selected_candidate.hard_mismatches),
                )
            ),
            candidates=[
                WebRunResultCandidate(
                    model_id=candidate.model_id,
                    label=display_model_label(candidate.model_id),
                    similarity=candidate.overall_similarity,
                    content_similarity=candidate.content_similarity,
                    capability_similarity=candidate.capability_similarity,
                    consistency=candidate.consistency,
                    answer_coverage_ratio=candidate.answer_coverage_ratio,
                    reasoning_coverage_ratio=candidate.reasoning_coverage_ratio,
                    capability_coverage_ratio=candidate.capability_coverage_ratio,
                    protocol_status=candidate.protocol_status,
                    protocol_issues=list(candidate.protocol_issues),
                    hard_mismatches=list(candidate.hard_mismatches),
                )
                for candidate in comparison.candidates
            ],
            dimensions=WebRunResultDimensions(
                content_similarity=comparison.dimensions.content_similarity,
                capability_similarity=comparison.dimensions.capability_similarity,
                answer_similarity=comparison.dimensions.answer_similarity,
                reasoning_similarity=comparison.dimensions.reasoning_similarity,
                transport_similarity=comparison.dimensions.transport_similarity,
                surface_similarity=comparison.dimensions.surface_similarity,
            ),
            coverage=WebRunResultCoverage(
                answer_coverage_ratio=comparison.coverage.answer_coverage_ratio,
                reasoning_coverage_ratio=comparison.coverage.reasoning_coverage_ratio,
                capability_coverage_ratio=comparison.coverage.capability_coverage_ratio,
                protocol_status=comparison.coverage.protocol_status,
            ),
            diagnostics=WebRunResultDiagnostics(
                protocol_status=comparison.coverage.protocol_status,
                protocol_issues=list(comparison.diagnostics.protocol_issues),
                hard_mismatches=list(comparison.diagnostics.hard_mismatches),
                blocking_reasons=blocking_reasons,
                recommendations=_build_recommendations(
                    result_state=result_state,
                    blocking_reasons=blocking_reasons,
                    selected_rank=selected_rank,
                    top_candidate_label=display_model_label(top_candidate.model_id),
                ),
            ),
            prompt_breakdown=[
                WebRunResultPromptBreakdown(
                    prompt_id=prompt.prompt_id,
                    status=prompt.status,
                    similarity=prompt.similarity,
                    scoreable=prompt.scoreable,
                    error_kind=prompt.error_kind,
                    error_message=prompt.error_message,
                )
                for prompt in comparison.prompt_breakdown
            ],
            thresholds_used=WebRunResultThresholds(
                match=comparison.thresholds_used.match,
                suspicious=comparison.thresholds_used.suspicious,
                unknown=comparison.thresholds_used.unknown,
                margin=comparison.thresholds_used.margin,
                consistency=comparison.thresholds_used.consistency,
                answer_min=comparison.thresholds_used.answer_min,
                reasoning_min=comparison.thresholds_used.reasoning_min,
            ),
        )

    def _execute_suite(
        self,
        *,
        run_id: str,
        input: WebRunInput,
        api_key: str,
        endpoint: EndpointProfile,
        capability_probe_payload: dict[str, object],
        progress_callback=None,
    ) -> RunArtifact:
        runtime_policy = resolve_runtime_policy(
            capability_probe_payload=capability_probe_payload,
            endpoint=endpoint,
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
                dialect=build_protocol_family_adapter(endpoint),
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
            progress_callback=progress_callback,
        )
        return RunArtifact.model_validate(json.loads(output_path.read_text(encoding="utf-8")))

    def _ensure_selected_fingerprint_exists(self, model_id: str) -> None:
        profile_path = self._paths.profiles_dir / WEB_FINGERPRINT_SUITE_ID / f"{model_id}.json"
        if not profile_path.exists():
            raise WebRunConfigurationError(
                code="UNKNOWN_FINGERPRINT_MODEL",
                message=f"unknown fingerprint model: {model_id}",
                field="fingerprintModel",
            )

    def _resolve_input_endpoint_profile(self, input: WebRunInput) -> EndpointProfile:
        profiles = load_endpoint_profiles(self._paths.endpoint_profiles_dir)
        try:
            return resolve_or_build_endpoint_profile(
                profiles,
                base_url=input.base_url,
                model=input.model_name,
            )
        except EndpointProfileResolutionError as exc:
            raise WebRunConfigurationError(
                code="AMBIGUOUS_ENDPOINT_PROFILE",
                message=str(exc),
                field="baseUrl",
            ) from exc

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
            field=exc.field,
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

    def _set_stage(
        self,
        run_id: str,
        stage_id: str,
        status: str,
        *,
        message: str | None,
        run_status: str | None = None,
    ) -> WebRunRecord:
        return self._store.update(
            run_id,
            lambda record, timestamp: record.model_copy(
                update={
                    "run_status": record.run_status if run_status is None else run_status,
                    "current_stage_id": stage_id,
                    "current_stage_message": message,
                    "stages": _update_stage_collection(
                        record.stages,
                        stage_id=stage_id,
                        status=status,
                        message=message,
                        timestamp=timestamp,
                    ),
                }
            ),
        )

    def _save_configuration_error(
        self,
        run_id: str,
        exc: WebRunConfigurationError,
        *,
        stage_id: str,
    ) -> WebRunRecord:
        failure = self._build_failure(exc)
        return self._store.update(
            run_id,
            lambda record, timestamp: record.model_copy(
                update={
                    "run_status": "configuration_error",
                    "result_state": "configuration_error",
                    "current_stage_id": stage_id,
                    "current_stage_message": exc.message,
                    "stages": _update_stage_collection(
                        record.stages,
                        stage_id=stage_id,
                        status="failed",
                        message=exc.message,
                        timestamp=timestamp,
                    ),
                    "failure": failure,
                }
            ),
        )

    def _raise_on_probe_configuration_failure(
        self,
        capability_probe_payload: dict[str, object],
    ) -> None:
        results = capability_probe_payload.get("results")
        if not isinstance(results, dict):
            return

        critical = [
            outcome
            for capability, outcome in results.items()
            if capability in {"thinking", "tools", "streaming"} and isinstance(outcome, dict)
        ]
        if not critical:
            return
        if any(
            outcome.get("status") in {"supported", "accepted_but_ignored"}
            for outcome in critical
        ):
            return

        http_statuses = [
            int(status)
            for outcome in critical
            for status in [outcome.get("http_status")]
            if isinstance(status, int)
        ]
        details = [
            str(detail)
            for outcome in critical
            for detail in [outcome.get("detail")]
            if isinstance(detail, str) and detail.strip() != ""
        ]
        detail_text = " | ".join(details) if details else None
        lower_detail = detail_text.lower() if detail_text is not None else ""

        if any(status in {401, 403} for status in http_statuses):
            raise WebRunConfigurationError(
                code="AUTH_FAILED",
                message=detail_text or "provider rejected the supplied API key",
                http_status=next(status for status in http_statuses if status in {401, 403}),
                retryable=False,
                field="apiKey",
            )
        if 429 in http_statuses or "rate limit" in lower_detail:
            raise WebRunConfigurationError(
                code="RATE_LIMITED",
                message=detail_text or "provider rejected the request due to rate limits",
                http_status=429,
                retryable=True,
            )
        if _looks_like_model_error(http_statuses, lower_detail):
            raise WebRunConfigurationError(
                code="MODEL_NOT_FOUND",
                message=detail_text or "provider could not find the requested model",
                http_status=http_statuses[0] if http_statuses else None,
                retryable=False,
                field="modelName",
            )
        if any(status >= 500 for status in http_statuses):
            raise WebRunConfigurationError(
                code="PROVIDER_SERVER_ERROR",
                message=(
                    detail_text
                    or "provider returned a server-side error during capability probe"
                ),
                http_status=next(status for status in http_statuses if status >= 500),
                retryable=True,
            )
        if http_statuses:
            raise WebRunConfigurationError(
                code="UNSUPPORTED_ENDPOINT_PROTOCOL",
                message=(
                    detail_text
                    or "endpoint did not behave like an OpenAI-compatible chat completion API"
                ),
                http_status=http_statuses[0],
                retryable=False,
                field="baseUrl",
            )

        raise WebRunConfigurationError(
            code="ENDPOINT_UNREACHABLE",
            message=(
                detail_text
                or "unable to reach the configured endpoint during capability probe"
            ),
            retryable=True,
            field="baseUrl",
        )

    def _suite_progress_callback(self, run_id: str):
        def callback(
            event: str,
            prompt: PromptDefinition,
            index: int,
            total: int,
            execution: PromptExecutionResult | None,
        ) -> None:
            if event == "prompt_started":
                self._store.update(
                    run_id,
                    lambda record, timestamp: record.model_copy(
                        update={
                            "current_stage_id": "prompt_execution",
                            "current_stage_message": f"running {prompt.id} ({index}/{total})",
                            "stages": _update_stage_collection(
                                record.stages,
                                stage_id="prompt_execution",
                                status="running",
                                message=f"running {prompt.id} ({index}/{total})",
                                timestamp=timestamp,
                            ),
                            "prompts": [
                                item
                                if item.prompt_id != prompt.id
                                else item.model_copy(
                                    update={
                                        "status": "running",
                                        "started_at": timestamp,
                                    }
                                )
                                for item in record.prompts
                            ],
                        }
                    ),
                )
                return

            if execution is None:
                return

            self._store.update(
                run_id,
                lambda record, timestamp: record.model_copy(
                    update={
                        "current_stage_id": "prompt_execution",
                        "current_stage_message": f"finished {prompt.id} ({index}/{total})",
                        "stages": _update_stage_collection(
                            record.stages,
                            stage_id="prompt_execution",
                            status="running",
                            message=f"finished {prompt.id} ({index}/{total})",
                            timestamp=timestamp,
                        ),
                        "prompts": [
                            item
                            if item.prompt_id != prompt.id
                            else _project_execution_prompt(
                                prompt=prompt,
                                execution=execution,
                                started_at=item.started_at,
                                finished_at=timestamp,
                            )
                            for item in record.prompts
                        ],
                    }
                ),
            )

        return callback

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
    attempt = prompt.attempts[-1] if prompt.attempts else None
    latency_ms = None
    if prompt.completion is not None and prompt.completion.latency_ms is not None:
        latency_ms = prompt.completion.latency_ms
    elif attempt is not None:
        latency_ms = attempt.latency_ms
    return WebRunPrompt(
        prompt_id=prompt.prompt_id,
        status=status,
        elapsed_seconds=None if latency_ms is None else latency_ms // 1000,
        elapsed_ms=latency_ms,
        summary_code=_summary_code_for_prompt(prompt.status),
        error_code=_error_code_for_prompt(prompt.status),
        error_kind=None if error is None else error.kind,
        error_detail=None if error is None else error.message,
        http_status=None if error is None else error.http_status,
        first_byte_ms=None if attempt is None else attempt.first_byte_latency_ms,
        bytes_received=None if attempt is None else attempt.bytes_received,
        finish_reason=(
            prompt.completion.finish_reason
            if prompt.completion is not None
            else None if attempt is None else attempt.finish_reason
        ),
        parse_status=_parse_status_for_prompt(prompt.status),
        answer_present=(
            None
            if prompt.completion is None
            else prompt.completion.answer_text.strip() != ""
        ),
        reasoning_present=(
            None if prompt.completion is None else prompt.completion.reasoning_visible
        ),
        scoreable=bool(prompt.features),
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


def _parse_status_for_prompt(status: str) -> str:
    return {
        "completed": "parsed",
        "timeout": "not_available",
        "transport_error": "not_available",
        "unsupported_capability": "unsupported",
        "truncated": "parse_failed",
        "invalid_response": "parse_failed",
        "canonicalization_error": "canonicalization_failed",
    }.get(status, "not_available")


def _project_execution_prompt(
    *,
    prompt: PromptDefinition,
    execution: PromptExecutionResult,
    started_at,
    finished_at,
) -> WebRunPrompt:
    error = execution.error
    attempt = execution.attempts[-1] if execution.attempts else None
    latency_ms = None
    if execution.completion is not None and execution.completion.latency_ms is not None:
        latency_ms = execution.completion.latency_ms
    elif attempt is not None:
        latency_ms = attempt.latency_ms

    return WebRunPrompt(
        prompt_id=prompt.id,
        status="completed" if execution.status == "completed" else "failed",
        started_at=started_at,
        finished_at=finished_at,
        elapsed_seconds=None if latency_ms is None else latency_ms // 1000,
        elapsed_ms=latency_ms,
        summary_code=_summary_code_for_prompt(execution.status),
        error_code=_error_code_for_prompt(execution.status),
        error_kind=None if error is None else error.kind,
        error_detail=None if error is None else error.message,
        http_status=(
            None
            if error is None
            else error.http_status
        ),
        first_byte_ms=None if attempt is None else attempt.first_byte_latency_ms,
        bytes_received=None if attempt is None else attempt.bytes_received,
        finish_reason=(
            execution.completion.finish_reason
            if execution.completion is not None
            else None if attempt is None else attempt.finish_reason
        ),
        parse_status=_parse_status_for_prompt(execution.status),
        answer_present=(
            None
            if execution.completion is None
            else execution.completion.answer_text.strip() != ""
        ),
        reasoning_present=(
            None
            if execution.completion is None
            else execution.completion.reasoning_visible
        ),
        scoreable=None,
    )


def _merge_prompt_metadata(existing_prompts, projected_prompts):
    existing_by_id = {prompt.prompt_id: prompt for prompt in existing_prompts}
    merged = []
    for prompt in projected_prompts:
        existing = existing_by_id.get(prompt.prompt_id)
        if existing is None:
            merged.append(prompt)
            continue
        merged.append(
            prompt.model_copy(
                update={
                    "started_at": existing.started_at,
                    "finished_at": existing.finished_at,
                }
            )
        )
    return merged


def _update_stage_collection(
    stages,
    *,
    stage_id: str,
    status: str,
    message: str | None,
    timestamp,
):
    updated_stages = []
    for stage in stages:
        if stage.id != stage_id:
            updated_stages.append(stage)
            continue

        updates = {
            "status": status,
            "message": message,
        }
        if status == "running" and stage.started_at is None:
            updates["started_at"] = timestamp
        if status in {"completed", "failed"}:
            updates["finished_at"] = timestamp
        updated_stages.append(stage.model_copy(update=updates))
    return updated_stages


def _looks_like_model_error(http_statuses: list[int], detail: str) -> bool:
    if any(status == 404 for status in http_statuses) and "model" in detail:
        return True
    return any(
        token in detail
        for token in [
            "model not found",
            "unknown model",
            "does not exist",
            "invalid model",
            "\"model\"",
        ]
    )


def _probe_summary_message(payload: dict[str, object]) -> str:
    results = payload.get("results")
    if not isinstance(results, dict):
        return "capability probe completed"
    parts = []
    for capability in ("thinking", "tools", "streaming", "image"):
        outcome = results.get(capability)
        if isinstance(outcome, dict):
            status = outcome.get("status")
            if isinstance(status, str):
                parts.append(f"{capability}={status}")
    if not parts:
        return "capability probe completed"
    return "capability probe completed: " + ", ".join(parts)


def _build_blocking_reasons(comparison) -> list[str]:
    reasons: list[str] = []
    if comparison.coverage.protocol_status != "compatible":
        reasons.append(f"protocol_status={comparison.coverage.protocol_status}")
    if comparison.coverage.answer_coverage_ratio < comparison.thresholds_used.answer_min:
        reasons.append(
            "answer coverage below threshold "
            f"({comparison.coverage.answer_coverage_ratio:.2f} < "
            f"{comparison.thresholds_used.answer_min:.2f})"
        )
    if comparison.coverage.reasoning_coverage_ratio < comparison.thresholds_used.reasoning_min:
        reasons.append(
            "reasoning coverage below threshold "
            f"({comparison.coverage.reasoning_coverage_ratio:.2f} < "
            f"{comparison.thresholds_used.reasoning_min:.2f})"
        )
    for prompt in comparison.prompt_breakdown:
        if not prompt.scoreable:
            detail = prompt.error_kind or prompt.status
            reasons.append(f"{prompt.prompt_id}: {detail}")
    reasons.extend(comparison.diagnostics.protocol_issues)
    return reasons


def _build_recommendations(
    *,
    result_state: str,
    blocking_reasons: list[str],
    selected_rank: int | None,
    top_candidate_label: str,
) -> list[str]:
    recommendations: list[str] = []
    joined = " ".join(blocking_reasons).lower()
    if result_state == "insufficient_evidence":
        recommendations.append(
            "Resolve the blocking prompt failures and rerun to reach "
            "at least 3 scoreable prompts."
        )
    if "timeout" in joined or "transport_error" in joined:
        recommendations.append(
            "Verify provider latency, endpoint reachability, and rate limits "
            "before rerunning."
        )
    if "parse" in joined or "canonicalization" in joined or "truncated" in joined:
        recommendations.append(
            "Verify the endpoint can return stable structured JSON for the "
            "V3 prompt suite."
        )
    if result_state in {"formal_result", "provisional"} and selected_rank not in (None, 1):
        recommendations.append(
            "The selected fingerprint is not the closest candidate. "
            f"Inspect {top_candidate_label} as the nearest match."
        )
    if not recommendations:
        recommendations.append(
            "Review the prompt diagnostics table for per-prompt transport "
            "and parsing details."
        )
    return recommendations


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
