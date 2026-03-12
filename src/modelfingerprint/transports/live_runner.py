from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from modelfingerprint.canonicalizers.base import CanonicalizationError
from modelfingerprint.canonicalizers.tolerant_json import canonicalize_tolerant_json
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import (
    NormalizedCompletion,
    PromptAttemptSummary,
    PromptExecutionError,
    PromptRequestSnapshot,
    RuntimeAttemptPolicy,
    RuntimePolicySnapshot,
    RuntimeRequestIntent,
)
from modelfingerprint.dialects.base import (
    DialectAdapter,
    HttpRequestSpec,
    build_protocol_family_adapter,
)
from modelfingerprint.services.feature_pipeline import (
    PromptExecutionResult,
    PromptExecutionStatus,
)
from modelfingerprint.storage.filesystem import ensure_directories
from modelfingerprint.services.runtime_policy import (
    resolve_output_token_cap,
    resolve_runtime_attempts,
)
from modelfingerprint.transports.http_client import (
    HttpClient,
    HttpClientError,
    HttpProgressSnapshot,
    HttpTerminalResult,
    InFlightHttpRequest,
    StandardHttpClient,
)


@dataclass(frozen=True)
class _RuntimeAttemptOutcome:
    status: PromptExecutionStatus
    raw_output: str | None = None
    usage: object | None = None
    completion: NormalizedCompletion | None = None
    error: PromptExecutionError | None = None
    attempt_summary: PromptAttemptSummary | None = None


class LiveRunner:
    def __init__(
        self,
        *,
        endpoint: EndpointProfile,
        api_key: str,
        dialect: DialectAdapter | None = None,
        http_client: HttpClient | None = None,
        trace_dir: Path | None = None,
        runtime_policy: RuntimePolicySnapshot | None = None,
    ) -> None:
        self.endpoint = endpoint
        self._api_key = api_key
        self._dialect = dialect or build_protocol_family_adapter(endpoint)
        self._http_client = http_client or StandardHttpClient()
        self.trace_dir = trace_dir
        self._runtime_policy = runtime_policy
        self.runtime_policy = runtime_policy

    def execute(self, prompt: PromptDefinition) -> PromptExecutionResult:
        request_snapshot = PromptRequestSnapshot(
            messages=prompt.messages,
            generation=prompt.generation,
        )
        if self._runtime_policy is not None:
            return self._execute_with_runtime_policy(prompt, request_snapshot)

        return self._execute_legacy(prompt, request_snapshot)

    def _execute_legacy(
        self,
        prompt: PromptDefinition,
        request_snapshot: PromptRequestSnapshot,
    ) -> PromptExecutionResult:
        attempt_count = 1 + (
            0
            if self.endpoint.thinking_policy is None
            else len(self.endpoint.thinking_policy.attempts)
        )
        last_result: PromptExecutionResult | None = None

        for thinking_attempt_index in range(1, attempt_count + 1):
            request = self._dialect.build_request(
                prompt,
                self.endpoint,
                self._api_key,
                output_token_cap=_output_token_cap_for_attempt(
                    prompt,
                    self.endpoint,
                    thinking_attempt_index,
                ),
                body_overrides=_body_overrides_for_attempt(self.endpoint, thinking_attempt_index),
            )
            request_trace_path, response_trace_path = self._trace_paths(
                prompt.id,
                thinking_attempt_index,
            )
            if request_trace_path is not None:
                self._write_request_trace(request_trace_path, request)

            payload, latency_ms, transport_error = self._send_request(request)
            if transport_error is not None:
                return PromptExecutionResult(
                    prompt=prompt,
                    status="timeout" if _is_timeout_error_kind(transport_error.kind) else "transport_error",
                    request_snapshot=request_snapshot,
                    error=transport_error,
                )
            assert payload is not None

            if response_trace_path is not None:
                response_trace_path.write_text(
                    json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

            completion = self._dialect.parse_response(
                self.endpoint,
                payload,
                latency_ms=latency_ms,
                raw_response_path=None if response_trace_path is None else str(response_trace_path),
            )
            status, error = _classify_completion(prompt, completion)
            last_result = PromptExecutionResult(
                prompt=prompt,
                    status=status,
                    raw_output=completion.answer_text,
                    usage=completion.usage,
                    request_snapshot=request_snapshot,
                    completion=completion,
                    attempts=[],
                    error=error,
                )
            if not _should_retry_with_thinking_fallback(
                endpoint=self.endpoint,
                completion=completion,
                status=status,
                thinking_attempt_index=thinking_attempt_index,
                attempt_count=attempt_count,
            ):
                return last_result

        assert last_result is not None
        return last_result

    def _execute_with_runtime_policy(
        self,
        prompt: PromptDefinition,
        request_snapshot: PromptRequestSnapshot,
    ) -> PromptExecutionResult:
        assert self._runtime_policy is not None
        runtime_intent, attempt_policies = resolve_runtime_attempts(
            runtime_policy=self._runtime_policy,
            prompt=prompt,
        )
        attempt_summaries: list[PromptAttemptSummary] = []
        last_outcome: _RuntimeAttemptOutcome | None = None

        for tier_index, attempt_policy in enumerate(attempt_policies):
            output_token_cap = resolve_output_token_cap(
                prompt=prompt,
                endpoint=self.endpoint,
                attempt=attempt_policy,
            )
            request = self._dialect.build_request(
                prompt,
                self.endpoint,
                self._api_key,
                output_token_cap=output_token_cap,
                body_overrides=attempt_policy.request_body_overrides or None,
            )
            request_trace_path, response_trace_path = self._trace_paths(
                prompt.id,
                attempt_policy.attempt_index,
            )
            if request_trace_path is not None:
                self._write_request_trace(request_trace_path, request)

            if not _should_monitor_request(request):
                outcome = self._execute_blocking_runtime_request(
                    prompt=prompt,
                    request=request,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    response_trace_path=response_trace_path,
                )
            else:
                outcome = self._execute_streaming_runtime_request(
                    prompt=prompt,
                    request=request,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    response_trace_path=response_trace_path,
                )

            assert outcome.attempt_summary is not None
            attempt_summaries.append(outcome.attempt_summary)
            last_outcome = outcome
            if not _should_retry_runtime_attempt(
                attempt_policy=attempt_policy,
                outcome=outcome,
                has_next_attempt=tier_index + 1 < len(attempt_policies),
            ):
                break

        assert last_outcome is not None
        return PromptExecutionResult(
            prompt=prompt,
            status=last_outcome.status,
            raw_output=last_outcome.raw_output,
            usage=last_outcome.usage,
            request_snapshot=request_snapshot,
            completion=last_outcome.completion,
            attempts=attempt_summaries,
            error=last_outcome.error,
        )

    def _execute_blocking_runtime_request(
        self,
        *,
        prompt: PromptDefinition,
        request: HttpRequestSpec,
        runtime_intent: RuntimeRequestIntent,
        runtime_tier_index: int,
        attempt_policy: RuntimeAttemptPolicy,
        output_token_cap: int | None,
        response_trace_path: Path | None,
    ) -> _RuntimeAttemptOutcome:
        payload, latency_ms, transport_error = self._send_request(
            request,
            connect_timeout_seconds=attempt_policy.connect_timeout_seconds,
            read_timeout_seconds=attempt_policy.total_deadline_seconds,
        )
        if transport_error is not None:
            status = _transport_error_status(transport_error)
            return _RuntimeAttemptOutcome(
                status=status,
                error=transport_error,
                attempt_summary=_build_blocking_attempt_summary(
                    request_attempt_index=attempt_policy.attempt_index,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=runtime_tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    status=status,
                    error=transport_error,
                    answer_text_present=False,
                    completed=False,
                ),
            )
        assert payload is not None

        if response_trace_path is not None:
            response_trace_path.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        try:
            completion = self._dialect.parse_response(
                self.endpoint,
                payload,
                latency_ms=latency_ms,
                raw_response_path=None if response_trace_path is None else str(response_trace_path),
            )
        except Exception as exc:
            parse_error = PromptExecutionError(
                kind="response_parse_error",
                message=str(exc) or "response parsing failed",
                retryable=False,
            )
            return _RuntimeAttemptOutcome(
                status="invalid_response",
                error=parse_error,
                attempt_summary=_build_blocking_attempt_summary(
                    request_attempt_index=attempt_policy.attempt_index,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=runtime_tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    status="invalid_response",
                    error=parse_error,
                    latency_ms=latency_ms,
                    completed=True,
                ),
            )

        completion_status, completion_error = _classify_completion(prompt, completion)
        completion_status, completion_error = _validate_runtime_completion(
            prompt=prompt,
            completion=completion,
            status=completion_status,
            error=completion_error,
        )
        return _RuntimeAttemptOutcome(
            status=completion_status,
            raw_output=completion.answer_text,
            usage=completion.usage,
            completion=completion,
            error=completion_error,
            attempt_summary=_build_blocking_attempt_summary(
                request_attempt_index=attempt_policy.attempt_index,
                runtime_intent=runtime_intent,
                runtime_tier_index=runtime_tier_index,
                attempt_policy=attempt_policy,
                output_token_cap=output_token_cap,
                status=completion_status,
                error=completion_error,
                latency_ms=completion.latency_ms,
                finish_reason=completion.finish_reason,
                answer_text_present=completion.answer_text.strip() != "",
                reasoning_visible=completion.reasoning_visible,
                completed=True,
            ),
        )

    def _execute_streaming_runtime_request(
        self,
        *,
        prompt: PromptDefinition,
        request: HttpRequestSpec,
        runtime_intent: RuntimeRequestIntent,
        runtime_tier_index: int,
        attempt_policy: RuntimeAttemptPolicy,
        output_token_cap: int | None,
        response_trace_path: Path | None,
    ) -> _RuntimeAttemptOutcome:
        handle, start_error = self._start_request(
            request,
            attempt_policy=attempt_policy,
        )
        if start_error is not None:
            status = _transport_error_status(start_error)
            return _RuntimeAttemptOutcome(
                status=status,
                error=start_error,
                attempt_summary=_build_attempt_summary(
                    request_attempt_index=attempt_policy.attempt_index,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=runtime_tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    status=status,
                    error=start_error,
                    snapshot=HttpProgressSnapshot(
                        bytes_received=0,
                        has_any_data=False,
                        elapsed_ms=0,
                        completed=False,
                    ),
                ),
            )
        assert handle is not None

        terminal, snapshot, abort_reason = self._monitor_inflight_request(
            handle,
            attempt_policy=attempt_policy,
        )
        if terminal is None:
            timeout_error = PromptExecutionError(
                kind=abort_reason or "request_monitor_timeout",
                message=_abort_reason_message(abort_reason),
                retryable=False,
            )
            return _RuntimeAttemptOutcome(
                status="timeout",
                error=timeout_error,
                attempt_summary=_build_attempt_summary(
                    request_attempt_index=attempt_policy.attempt_index,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=runtime_tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    status="timeout",
                    error=timeout_error,
                    snapshot=snapshot,
                ),
            )

        if terminal.error is not None:
            transport_error = PromptExecutionError(
                kind=terminal.error.kind,
                message=terminal.error.message,
                retryable=False,
                http_status=terminal.error.status_code,
            )
            status = _transport_error_status(transport_error)
            return _RuntimeAttemptOutcome(
                status=status,
                error=transport_error,
                attempt_summary=_build_attempt_summary(
                    request_attempt_index=attempt_policy.attempt_index,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=runtime_tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    status=status,
                    error=transport_error,
                    snapshot=snapshot,
                    latency_ms=terminal.latency_ms,
                ),
            )

        assert terminal.payload is not None
        if response_trace_path is not None:
            response_trace_path.write_text(
                json.dumps(terminal.payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

        try:
            completion = self._dialect.parse_response(
                self.endpoint,
                terminal.payload,
                latency_ms=terminal.latency_ms,
                raw_response_path=None if response_trace_path is None else str(response_trace_path),
            )
        except Exception as exc:
            parse_error = PromptExecutionError(
                kind="response_parse_error",
                message=str(exc) or "response parsing failed",
                retryable=False,
            )
            return _RuntimeAttemptOutcome(
                status="invalid_response",
                error=parse_error,
                attempt_summary=_build_attempt_summary(
                    request_attempt_index=attempt_policy.attempt_index,
                    runtime_intent=runtime_intent,
                    runtime_tier_index=runtime_tier_index,
                    attempt_policy=attempt_policy,
                    output_token_cap=output_token_cap,
                    status="invalid_response",
                    error=parse_error,
                    snapshot=snapshot,
                    latency_ms=terminal.latency_ms,
                    completed=True,
                ),
            )

        completion_status, completion_error = _classify_completion(prompt, completion)
        completion_status, completion_error = _validate_runtime_completion(
            prompt=prompt,
            completion=completion,
            status=completion_status,
            error=completion_error,
        )
        return _RuntimeAttemptOutcome(
            status=completion_status,
            raw_output=completion.answer_text,
            usage=completion.usage,
            completion=completion,
            error=completion_error,
            attempt_summary=_build_attempt_summary(
                request_attempt_index=attempt_policy.attempt_index,
                runtime_intent=runtime_intent,
                runtime_tier_index=runtime_tier_index,
                attempt_policy=attempt_policy,
                output_token_cap=output_token_cap,
                status=completion_status,
                error=completion_error,
                snapshot=snapshot,
                latency_ms=completion.latency_ms,
                finish_reason=completion.finish_reason,
                answer_text_present=completion.answer_text.strip() != "",
                reasoning_visible=completion.reasoning_visible,
                completed=True,
            ),
        )

    def _write_request_trace(self, path: Path, request: HttpRequestSpec) -> None:
        headers = dict(request.headers)
        if "Authorization" in headers:
            headers["Authorization"] = "Bearer ***REDACTED***"
        payload = {
            "url": request.url,
            "headers": headers,
            "body": request.body,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _send_request(
        self,
        request: HttpRequestSpec,
        *,
        connect_timeout_seconds: int | None = None,
        read_timeout_seconds: int | None = None,
    ) -> tuple[dict[str, object] | None, int | None, PromptExecutionError | None]:
        last_error: PromptExecutionError | None = None
        for attempt in range(1, self.endpoint.retry_policy.max_attempts + 1):
            try:
                payload, latency_ms = self._http_client.send(
                    request,
                    connect_timeout_seconds=(
                        self.endpoint.timeout_policy.connect_seconds
                        if connect_timeout_seconds is None
                        else connect_timeout_seconds
                    ),
                    read_timeout_seconds=(
                        self.endpoint.timeout_policy.read_seconds
                        if read_timeout_seconds is None
                        else read_timeout_seconds
                    ),
                )
                return payload, latency_ms, None
            except HttpClientError as exc:
                retryable = _is_retryable(exc, self.endpoint.retry_policy.retryable_statuses)
                last_error = PromptExecutionError(
                    kind=exc.kind,
                    message=exc.message,
                    retryable=retryable,
                    http_status=exc.status_code,
                )
                if retryable and attempt < self.endpoint.retry_policy.max_attempts:
                    continue
                return None, None, last_error
            except Exception as exc:
                return (
                    None,
                    None,
                    PromptExecutionError(
                        kind="transport_runtime_error",
                        message=str(exc) or "transport runtime error",
                        retryable=False,
                    ),
                )
        return None, None, last_error

    def _start_request(
        self,
        request: HttpRequestSpec,
        *,
        attempt_policy: RuntimeAttemptPolicy,
    ) -> tuple[InFlightHttpRequest | None, PromptExecutionError | None]:
        start = getattr(self._http_client, "start", None)
        if not callable(start):
            return (
                None,
                PromptExecutionError(
                    kind="unsupported_transport",
                    message="http client does not support in-flight request monitoring",
                    retryable=False,
                ),
            )
        try:
            handle = start(
                request,
                connect_timeout_seconds=attempt_policy.connect_timeout_seconds,
                read_timeout_seconds=attempt_policy.total_deadline_seconds,
            )
            return handle, None
        except HttpClientError as exc:
            return (
                None,
                PromptExecutionError(
                    kind=exc.kind,
                    message=exc.message,
                    retryable=_is_retryable(exc, self.endpoint.retry_policy.retryable_statuses),
                    http_status=exc.status_code,
                ),
            )
        except Exception as exc:
            return (
                None,
                PromptExecutionError(
                    kind="transport_runtime_error",
                    message=str(exc) or "transport runtime error",
                    retryable=False,
                ),
            )

    def _monitor_inflight_request(
        self,
        handle: InFlightHttpRequest,
        *,
        attempt_policy: RuntimeAttemptPolicy,
    ) -> tuple[HttpTerminalResult | None, HttpProgressSnapshot, str | None]:
        terminal = handle.wait_until_terminal(float(attempt_policy.first_byte_timeout_seconds))
        snapshot = handle.snapshot()
        if terminal is not None:
            return terminal, snapshot, None
        if snapshot.has_any_data:
            return self._poll_inflight_progress(handle, attempt_policy=attempt_policy)
        self._cancel_inflight_request(handle)
        return None, handle.snapshot(), "first_byte_timeout"

    def _poll_inflight_progress(
        self,
        handle: InFlightHttpRequest,
        *,
        attempt_policy: RuntimeAttemptPolicy,
    ) -> tuple[HttpTerminalResult | None, HttpProgressSnapshot, str | None]:
        while True:
            snapshot = handle.snapshot()
            remaining_seconds = (
                attempt_policy.total_deadline_seconds - snapshot.elapsed_ms / 1000.0
            )
            if remaining_seconds <= 0:
                self._cancel_inflight_request(handle)
                return None, handle.snapshot(), "total_deadline_exceeded"

            terminal = handle.wait_until_terminal(
                float(min(attempt_policy.idle_timeout_seconds, remaining_seconds))
            )
            snapshot = handle.snapshot()
            if terminal is not None:
                return terminal, snapshot, None
            last_progress_ms = snapshot.last_progress_latency_ms or snapshot.first_byte_latency_ms
            if last_progress_ms is not None:
                if snapshot.elapsed_ms - last_progress_ms >= attempt_policy.idle_timeout_seconds * 1000:
                    self._cancel_inflight_request(handle)
                    return None, handle.snapshot(), "idle_timeout"
            if snapshot.elapsed_ms >= attempt_policy.total_deadline_seconds * 1000:
                self._cancel_inflight_request(handle)
                return None, handle.snapshot(), "total_deadline_exceeded"

    def _cancel_inflight_request(self, handle: InFlightHttpRequest) -> None:
        handle.cancel()
        handle.wait_until_terminal(2.0)

    def _trace_paths(
        self,
        prompt_id: str,
        thinking_attempt_index: int,
    ) -> tuple[Path | None, Path | None]:
        if self.trace_dir is None:
            return None, None
        ensure_directories(self.trace_dir)
        suffix = "" if thinking_attempt_index == 1 else f".attempt-{thinking_attempt_index}"
        return (
            self.trace_dir / f"{prompt_id}{suffix}.request.json",
            self.trace_dir / f"{prompt_id}{suffix}.response.json",
        )


def _classify_completion(
    prompt: PromptDefinition,
    completion: NormalizedCompletion,
) -> tuple[PromptExecutionStatus, PromptExecutionError | None]:
    if completion.answer_text.strip() == "":
        return (
            "invalid_response",
            PromptExecutionError(
                kind="missing_answer_text",
                message="response did not include answer text",
                retryable=False,
            ),
        )
    if completion.finish_reason == "length" and not _can_accept_length_terminated_output(
        prompt=prompt,
        completion=completion,
    ):
        return (
            "truncated",
            PromptExecutionError(
                kind="truncated_output",
                message="response hit the configured output-token cap",
                retryable=False,
            ),
        )
    if prompt.generation.reasoning_mode == "require_visible" and not completion.reasoning_visible:
        return (
            "invalid_response",
            PromptExecutionError(
                kind="missing_reasoning_text",
                message="prompt requires visible reasoning but none was returned",
                retryable=False,
            ),
        )
    return "completed", None


def _can_accept_length_terminated_output(
    *,
    prompt: PromptDefinition,
    completion: NormalizedCompletion,
) -> bool:
    if completion.answer_text.strip() == "":
        return False
    return prompt.output_contract.canonicalizer == "tolerant_json_v3"


def _is_retryable(error: HttpClientError, retryable_statuses: list[int]) -> bool:
    if error.kind in {"timeout", "network"}:
        return True
    if error.kind == "http_status" and error.status_code in retryable_statuses:
        return True
    return False


def _should_retry_with_thinking_fallback(
    *,
    endpoint: EndpointProfile,
    completion: NormalizedCompletion,
    status: PromptExecutionStatus,
    thinking_attempt_index: int,
    attempt_count: int,
) -> bool:
    policy = endpoint.thinking_policy
    if policy is None or thinking_attempt_index >= attempt_count:
        return False
    if status == "truncated" and completion.finish_reason in policy.retry_on_finish_reasons:
        return True
    if status == "invalid_response" and policy.retry_on_empty_answer:
        return completion.answer_text.strip() == ""
    return False


def _transport_error_status(error: PromptExecutionError) -> PromptExecutionStatus:
    if _is_timeout_error_kind(error.kind):
        return "timeout"
    if error.kind == "invalid_json":
        return "invalid_response"
    return "transport_error"


def _is_timeout_error_kind(kind: str) -> bool:
    return kind in {
        "timeout",
        "connect_timeout",
        "first_byte_timeout",
        "idle_timeout",
        "total_deadline_exceeded",
    }


def _abort_reason_message(abort_reason: str | None) -> str:
    if abort_reason == "first_byte_timeout":
        return "response did not arrive before the first byte deadline"
    if abort_reason == "idle_timeout":
        return "response stream was idle past the idle timeout"
    if abort_reason == "total_deadline_exceeded":
        return "request did not complete before the total runtime deadline"
    return "request monitoring timed out"


def _should_monitor_request(request: HttpRequestSpec) -> bool:
    accept = str(request.headers.get("Accept", ""))
    if "text/event-stream" in accept.lower():
        return True
    return request.body.get("stream") is True


def _build_attempt_summary(
    *,
    request_attempt_index: int,
    runtime_intent: RuntimeRequestIntent,
    runtime_tier_index: int,
    attempt_policy: RuntimeAttemptPolicy,
    output_token_cap: int | None,
    status: PromptExecutionStatus,
    error: PromptExecutionError | None,
    snapshot: HttpProgressSnapshot,
    latency_ms: int | None = None,
    finish_reason: str | None = None,
    answer_text_present: bool = False,
    reasoning_visible: bool | None = None,
    completed: bool | None = None,
) -> PromptAttemptSummary:
    return PromptAttemptSummary(
        request_attempt_index=request_attempt_index,
        read_timeout_seconds=attempt_policy.total_deadline_seconds,
        runtime_intent=runtime_intent,
        runtime_tier_index=runtime_tier_index,
        output_token_cap=output_token_cap,
        connect_timeout_seconds=attempt_policy.connect_timeout_seconds,
        write_timeout_seconds=attempt_policy.write_timeout_seconds,
        first_byte_timeout_seconds=attempt_policy.first_byte_timeout_seconds,
        idle_timeout_seconds=attempt_policy.idle_timeout_seconds,
        total_deadline_seconds=attempt_policy.total_deadline_seconds,
        status=status,
        error_kind=None if error is None else error.kind,
        http_status=None if error is None else error.http_status,
        latency_ms=latency_ms if latency_ms is not None else snapshot.elapsed_ms,
        finish_reason=finish_reason,
        answer_text_present=answer_text_present,
        reasoning_visible=reasoning_visible,
        bytes_received=snapshot.bytes_received,
        first_byte_latency_ms=snapshot.first_byte_latency_ms,
        last_progress_latency_ms=snapshot.last_progress_latency_ms,
        completed=snapshot.completed if completed is None else completed,
        abort_reason=None if error is None or status != "timeout" else error.kind,
    )


def _build_blocking_attempt_summary(
    *,
    request_attempt_index: int,
    runtime_intent: RuntimeRequestIntent,
    runtime_tier_index: int,
    attempt_policy: RuntimeAttemptPolicy,
    output_token_cap: int | None,
    status: PromptExecutionStatus,
    error: PromptExecutionError | None,
    latency_ms: int | None = None,
    finish_reason: str | None = None,
    answer_text_present: bool = False,
    reasoning_visible: bool | None = None,
    completed: bool | None = None,
) -> PromptAttemptSummary:
    return PromptAttemptSummary(
        request_attempt_index=request_attempt_index,
        read_timeout_seconds=attempt_policy.total_deadline_seconds,
        runtime_intent=runtime_intent,
        runtime_tier_index=runtime_tier_index,
        output_token_cap=output_token_cap,
        connect_timeout_seconds=attempt_policy.connect_timeout_seconds,
        write_timeout_seconds=attempt_policy.write_timeout_seconds,
        first_byte_timeout_seconds=attempt_policy.first_byte_timeout_seconds,
        idle_timeout_seconds=attempt_policy.idle_timeout_seconds,
        total_deadline_seconds=attempt_policy.total_deadline_seconds,
        status=status,
        error_kind=None if error is None else error.kind,
        http_status=None if error is None else error.http_status,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        answer_text_present=answer_text_present,
        reasoning_visible=reasoning_visible,
        bytes_received=None,
        first_byte_latency_ms=None,
        last_progress_latency_ms=None,
        completed=completed,
        abort_reason=None if error is None or status != "timeout" else error.kind,
    )


def _validate_runtime_completion(
    *,
    prompt: PromptDefinition,
    completion: NormalizedCompletion,
    status: PromptExecutionStatus,
    error: PromptExecutionError | None,
) -> tuple[PromptExecutionStatus, PromptExecutionError | None]:
    if status != "completed":
        return status, error
    if _requires_structured_output(prompt):
        try:
            canonicalize_tolerant_json(completion.answer_text)
        except CanonicalizationError:
            return (
                "invalid_response",
                PromptExecutionError(
                    kind="invalid_structured_output",
                    message="response did not contain valid structured output",
                    retryable=False,
                ),
            )
    return status, error


def _requires_structured_output(prompt: PromptDefinition) -> bool:
    return (
        prompt.generation.response_format == "json_object"
        or prompt.output_contract.canonicalizer == "tolerant_json_v3"
    )


def _should_retry_runtime_attempt(
    *,
    attempt_policy: RuntimeAttemptPolicy,
    outcome: _RuntimeAttemptOutcome,
    has_next_attempt: bool,
) -> bool:
    if not has_next_attempt:
        return False
    retry_signals = _runtime_retry_signals(
        status=outcome.status,
        completion=outcome.completion,
        error=outcome.error,
    )
    return any(signal in attempt_policy.escalate_on for signal in retry_signals)


def _runtime_retry_signals(
    *,
    status: PromptExecutionStatus,
    completion: NormalizedCompletion | None,
    error: PromptExecutionError | None,
) -> set[str]:
    signals: set[str] = set()
    if status == "truncated" and completion is not None and completion.finish_reason == "length":
        signals.add("finish_reason_length")
    if error is not None:
        if error.kind == "missing_answer_text":
            signals.add("missing_answer_text")
        if error.kind == "invalid_structured_output":
            signals.add("invalid_structured_output")
        if error.kind == "missing_reasoning_text":
            signals.add("missing_reasoning_text")
        if status in {"timeout", "transport_error"} and error.retryable:
            signals.add("retryable_transport_error")
    return signals


def _output_token_cap_for_attempt(
    prompt: PromptDefinition,
    endpoint: EndpointProfile,
    thinking_attempt_index: int,
) -> int | None:
    if endpoint.thinking_policy is None or thinking_attempt_index == 1:
        return None
    attempt = endpoint.thinking_policy.attempts[thinking_attempt_index - 2]
    if attempt.output_token_cap is not None:
        return attempt.output_token_cap
    if attempt.output_token_cap_multiplier is not None:
        return int(
            math.ceil(
                prompt.generation.max_output_tokens
                * attempt.output_token_cap_multiplier
            )
        )
    return None


def _body_overrides_for_attempt(
    endpoint: EndpointProfile,
    thinking_attempt_index: int,
) -> dict[str, object] | None:
    if endpoint.thinking_policy is None or thinking_attempt_index == 1:
        return None
    overrides = endpoint.thinking_policy.attempts[thinking_attempt_index - 2].request_body_overrides
    if not overrides:
        return None
    return overrides
