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

        return self
