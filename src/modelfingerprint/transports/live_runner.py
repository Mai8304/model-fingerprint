from __future__ import annotations

import json
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
        request = self._dialect.build_request(prompt, self.endpoint, self._api_key)
        request_snapshot = PromptRequestSnapshot(
            messages=prompt.messages,
            generation=prompt.generation,
        )
        request_trace_path = None
        response_trace_path = None
        if self.trace_dir is not None:
            ensure_directories(self.trace_dir)
            request_trace_path = self.trace_dir / f"{prompt.id}.request.json"
            response_trace_path = self.trace_dir / f"{prompt.id}.response.json"
            self._write_request_trace(request_trace_path, request)

        last_error: PromptExecutionError | None = None
        for attempt in range(1, self.endpoint.retry_policy.max_attempts + 1):
            try:
                payload, latency_ms = self._http_client.send(
                    request,
                    connect_timeout_seconds=self.endpoint.timeout_policy.connect_seconds,
                    read_timeout_seconds=self.endpoint.timeout_policy.read_seconds,
                )
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
                return PromptExecutionResult(
                    prompt=prompt,
                    status="timeout" if exc.kind == "timeout" else "transport_error",
                    request_snapshot=request_snapshot,
                    error=last_error,
                )

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
            return PromptExecutionResult(
                prompt=prompt,
                status=status,
                raw_output=completion.answer_text,
                usage=completion.usage,
                request_snapshot=request_snapshot,
                completion=completion,
                error=error,
            )

        return PromptExecutionResult(
            prompt=prompt,
            status="transport_error",
            request_snapshot=request_snapshot,
            error=last_error,
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


def _classify_completion(
    prompt: PromptDefinition,
    completion: NormalizedCompletion,
) -> tuple[PromptExecutionStatus, PromptExecutionError | None]:
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
