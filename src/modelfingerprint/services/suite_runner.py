from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Protocol, cast

from modelfingerprint.adapters.openai_chat import ChatCompletionResult
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import (
    CapabilityProbeResult,
    PromptExecutionError,
    PromptRequestSnapshot,
    ProtocolCompatibility,
    RunArtifact,
    UsageMetadata,
)
from modelfingerprint.extractors.registry import ExtractorRegistry, build_default_registry
from modelfingerprint.services.endpoint_profiles import (
    EndpointProfileValidationError,
    ensure_endpoint_supports_prompt,
)
from modelfingerprint.services.feature_pipeline import FeaturePipeline, PromptExecutionResult
from modelfingerprint.services.prompt_bank import (
    FINGERPRINT_SUITE_ID,
    QUICK_CHECK_SUITE_ID,
    load_candidate_prompts,
    load_suites,
    validate_release_suite_subsets,
    validate_suite_references,
    validate_suite_subset,
)
from modelfingerprint.services.run_writer import RunWriter
from modelfingerprint.settings import RepositoryPaths


class PromptExecutionTransport(Protocol):
    def execute(self, prompt: PromptDefinition) -> PromptExecutionResult: ...


class LegacyCompletionTransport(Protocol):
    def complete(self, prompt: PromptDefinition) -> ChatCompletionResult: ...


class EndpointAwareTransport(Protocol):
    endpoint: EndpointProfile


class SuiteRunner:
    def __init__(
        self,
        paths: RepositoryPaths,
        transport: object,
        registry: ExtractorRegistry | None = None,
    ) -> None:
        self._paths = paths
        self._transport = transport
        self._registry = registry or build_default_registry(paths.root / "extractors")

    def run_suite(
        self,
        suite_id: str,
        target_label: str,
        claimed_model: str | None = None,
        run_date: date | None = None,
        capability_probe_payload: dict[str, object] | None = None,
    ) -> Path:
        prompts = load_candidate_prompts(self._paths.prompt_bank_dir / "candidates")
        suites = load_suites(self._paths.prompt_bank_dir / "suites")
        validate_suite_references(prompts, suites)
        validate_suite_subset(suites[FINGERPRINT_SUITE_ID], suites[QUICK_CHECK_SUITE_ID])
        validate_release_suite_subsets(suites)
        suite = suites[suite_id]
        executions: list[PromptExecutionResult] = []

        for prompt_id in suite.prompt_ids:
            prompt = prompts[prompt_id]
            executions.append(self._execute_prompt(prompt))

        artifact = FeaturePipeline(self._registry).build_run_artifact(
            run_id=f"{target_label}.{suite_id}",
            suite_id=suite.id,
            target_label=target_label,
            claimed_model=claimed_model,
            executions=executions,
        )
        artifact = self._enrich_artifact(
            artifact,
            prompts,
            suite.prompt_ids,
            capability_probe_payload=capability_probe_payload,
        )

        return RunWriter(self._paths).write(artifact, run_date or date.today())

    def _execute_prompt(self, prompt: PromptDefinition) -> PromptExecutionResult:
        request_snapshot = PromptRequestSnapshot(
            messages=prompt.messages,
            generation=prompt.generation,
        )
        if hasattr(self._transport, "endpoint"):
            try:
                endpoint_aware = cast(EndpointAwareTransport, self._transport)
                ensure_endpoint_supports_prompt(endpoint_aware.endpoint, prompt)
            except EndpointProfileValidationError as exc:
                return PromptExecutionResult(
                    prompt=prompt,
                    status="unsupported_capability",
                    request_snapshot=request_snapshot,
                    error=PromptExecutionError(
                        kind="unsupported_capability",
                        message=str(exc),
                        retryable=False,
                    ),
                )

        if hasattr(self._transport, "execute"):
            executor = cast(PromptExecutionTransport, self._transport)
            try:
                return executor.execute(prompt)
            except Exception as exc:
                return PromptExecutionResult(
                    prompt=prompt,
                    status="transport_error",
                    request_snapshot=request_snapshot,
                    error=PromptExecutionError(
                        kind="unexpected_transport_runtime_error",
                        message=str(exc) or "transport execution failed",
                        retryable=False,
                    ),
                )

        legacy_transport = cast(LegacyCompletionTransport, self._transport)
        try:
            result = legacy_transport.complete(prompt)
            return PromptExecutionResult(
                prompt=prompt,
                raw_output=result.content,
                usage=UsageMetadata(
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    total_tokens=result.total_tokens,
                ),
                request_snapshot=request_snapshot,
            )
        except Exception as exc:
            return PromptExecutionResult(
                prompt=prompt,
                status="transport_error",
                request_snapshot=request_snapshot,
                error=PromptExecutionError(
                    kind="unexpected_transport_runtime_error",
                    message=str(exc) or "legacy transport execution failed",
                    retryable=False,
                ),
            )

    def _enrich_artifact(
        self,
        artifact: RunArtifact,
        prompts: dict[str, PromptDefinition],
        prompt_ids: list[str],
        capability_probe_payload: dict[str, object] | None = None,
    ) -> RunArtifact:
        endpoint_profile_id = None
        trace_dir = None
        runtime_policy = None
        if hasattr(self._transport, "endpoint"):
            endpoint_aware = cast(EndpointAwareTransport, self._transport)
            endpoint_profile_id = endpoint_aware.endpoint.id
        if hasattr(self._transport, "trace_dir"):
            trace_dir = getattr(self._transport, "trace_dir")
        if hasattr(self._transport, "runtime_policy"):
            runtime_policy = getattr(self._transport, "runtime_policy")

        issues = [
            prompt.error.message
            for prompt in artifact.prompts
            if prompt.error is not None and prompt.error.message not in ("",)
        ]
        protocol_compatibility = ProtocolCompatibility(
            satisfied=not any(
                prompt.status == "unsupported_capability" for prompt in artifact.prompts
            ),
            required_capabilities=sorted(
                {
                    capability
                    for prompt_id in prompt_ids
                    for capability in prompts[prompt_id].required_capabilities
                }
            ),
            issues=issues,
        )

        return artifact.model_copy(
            update={
                "endpoint_profile_id": endpoint_profile_id,
                "trace_dir": None if trace_dir is None else str(trace_dir),
                "runtime_policy": runtime_policy,
                "capability_probe": _normalize_capability_probe_payload(capability_probe_payload),
                "protocol_compatibility": protocol_compatibility,
            }
        )


def _normalize_capability_probe_payload(
    payload: dict[str, object] | None,
) -> CapabilityProbeResult | None:
    if payload is None:
        return None
    raw_results = payload.get("results")
    if not isinstance(raw_results, dict):
        return None
    capabilities: dict[str, object] = {}
    for capability, raw_outcome in raw_results.items():
        if not isinstance(raw_outcome, dict):
            continue
        capabilities[capability] = {
            "status": raw_outcome.get("status"),
            "detail": raw_outcome.get("detail"),
            "http_status": raw_outcome.get("http_status"),
            "latency_ms": raw_outcome.get("latency_ms"),
            "evidence": raw_outcome.get("evidence", {}),
        }
    if not capabilities:
        return None
    return CapabilityProbeResult.model_validate(
        {
            "probe_mode": payload.get("probe_mode", "minimal"),
            "probe_version": payload.get("probe_version", "v1"),
            "coverage_ratio": payload.get("coverage_ratio", 0.0),
            "capabilities": capabilities,
        }
    )
