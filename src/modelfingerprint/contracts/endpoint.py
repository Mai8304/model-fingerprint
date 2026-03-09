from __future__ import annotations

from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from modelfingerprint.contracts._common import ContractModel


class EndpointAuth(ContractModel):
    kind: Literal["bearer_env"]
    env_var: str = Field(min_length=1)


class EndpointCapabilities(ContractModel):
    exposes_reasoning_text: bool = False
    supports_json_object_response: bool = False
    supports_temperature: bool = True
    supports_top_p: bool = True
    supports_output_token_cap: bool = True


class RequestMapping(ContractModel):
    output_token_cap_field: str = Field(min_length=1)
    json_response_shape: dict[str, object] | None = None
    static_body: dict[str, object] = Field(default_factory=dict)


class ThinkingAttempt(ContractModel):
    output_token_cap: int | None = Field(default=None, ge=1)
    output_token_cap_multiplier: float | None = Field(default=None, gt=1.0)
    request_body_overrides: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_attempt_shape(self) -> ThinkingAttempt:
        if (
            self.output_token_cap is None
            and self.output_token_cap_multiplier is None
            and not self.request_body_overrides
        ):
            raise ValueError("thinking attempt must change output budget or request body")
        if self.output_token_cap is not None and self.output_token_cap_multiplier is not None:
            raise ValueError(
                "thinking attempt cannot set both output_token_cap and output_token_cap_multiplier"
            )
        return self


class ThinkingPolicy(ContractModel):
    retry_on_finish_reasons: list[str] = Field(default_factory=lambda: ["length"])
    retry_on_empty_answer: bool = True
    attempts: list[ThinkingAttempt] = Field(min_length=1, max_length=4)


class UsagePaths(ContractModel):
    prompt_tokens: str = Field(min_length=1)
    output_tokens: str = Field(min_length=1)
    total_tokens: str = Field(min_length=1)
    reasoning_tokens: str | None = None


class ResponseMapping(ContractModel):
    answer_text_path: str = Field(min_length=1)
    reasoning_text_path: str | None = None
    finish_reason_path: str | None = None
    usage_paths: UsagePaths


class TimeoutPolicy(ContractModel):
    connect_seconds: int = Field(gt=0)
    read_seconds: int = Field(gt=0)


class RetryPolicy(ContractModel):
    max_attempts: int = Field(ge=1)
    retryable_statuses: list[int] = Field(default_factory=list)


class EndpointProfile(ContractModel):
    id: str = Field(min_length=1)
    dialect: str = Field(min_length=1)
    base_url: HttpUrl
    model: str = Field(min_length=1)
    auth: EndpointAuth
    capabilities: EndpointCapabilities
    request_mapping: RequestMapping
    response_mapping: ResponseMapping
    thinking_policy: ThinkingPolicy | None = None
    timeout_policy: TimeoutPolicy
    retry_policy: RetryPolicy

    @model_validator(mode="after")
    def validate_capability_shape(self) -> EndpointProfile:
        if (
            self.capabilities.exposes_reasoning_text
            and not self.response_mapping.reasoning_text_path
        ):
            raise ValueError(
                "reasoning_text_path is required when exposes_reasoning_text is true"
            )

        if (
            not self.capabilities.supports_json_object_response
            and self.request_mapping.json_response_shape is not None
        ):
            raise ValueError(
                "json_response_shape is not allowed when json object response is unsupported"
            )
        if (
            self.thinking_policy is not None
            and not self.capabilities.supports_output_token_cap
            and any(
                attempt.output_token_cap is not None
                or attempt.output_token_cap_multiplier is not None
                for attempt in self.thinking_policy.attempts
            )
        ):
            raise ValueError(
                "thinking policy cannot change output budget when output token caps are unsupported"
            )

        return self
