from __future__ import annotations

import json
import math
from pathlib import Path

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import (
    NormalizedCompletion,
    PromptExecutionError,
    PromptRequestSnapshot,
)
from modelfingerprint.dialects.base import DialectAdapter, HttpRequestSpec
from modelfingerprint.services.feature_pipeline import (
    PromptExecutionResult,
    PromptExecutionStatus,
)
from modelfingerprint.storage.filesystem import ensure_directories
from modelfingerprint.transports.http_client import HttpClient, HttpClientError, StandardHttpClient


class LiveRunner:
    def __init__(
        self,
        *,
        endpoint: EndpointProfile,
        api_key: str,
        dialect: DialectAdapter,
        http_client: HttpClient | None = None,
        trace_dir: Path | None = None,
    ) -> None:
        self.endpoint = endpoint
        self._api_key = api_key
        self._dialect = dialect
        self._http_client = http_client or StandardHttpClient()
        self.trace_dir = trace_dir

    def execute(self, prompt: PromptDefinition) -> PromptExecutionResult:
        request_snapshot = PromptRequestSnapshot(
            messages=prompt.messages,
            generation=prompt.generation,
        )
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
                    status="timeout"
                    if transport_error.kind == "timeout"
                    else "transport_error",
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
    ) -> tuple[dict[str, object] | None, int | None, PromptExecutionError | None]:
        last_error: PromptExecutionError | None = None
        for attempt in range(1, self.endpoint.retry_policy.max_attempts + 1):
            try:
                payload, latency_ms = self._http_client.send(
                    request,
                    connect_timeout_seconds=self.endpoint.timeout_policy.connect_seconds,
                    read_timeout_seconds=self.endpoint.timeout_policy.read_seconds,
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
        return None, None, last_error

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
    if completion.finish_reason == "length":
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
