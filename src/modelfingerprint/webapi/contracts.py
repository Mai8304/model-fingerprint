from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from modelfingerprint.contracts._common import ContractModel, SuiteId

WebRunStatus = Literal[
    "validating",
    "running",
    "completed",
    "configuration_error",
    "stopped",
]

WebResultState = Literal[
    "formal_result",
    "provisional",
    "insufficient_evidence",
    "incompatible_protocol",
    "configuration_error",
    "stopped",
]

WebPromptStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
    "stopped",
]


class WebFingerprintModel(ContractModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    suite_id: SuiteId
    available: bool


class WebRunInput(ContractModel):
    base_url: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    fingerprint_model_id: str = Field(min_length=1)


class WebRunPrompt(ContractModel):
    prompt_id: str = Field(min_length=1)
    status: WebPromptStatus
    elapsed_seconds: int | None = Field(default=None, ge=0)
    summary_code: str | None = None
    error_code: str | None = None
    error_detail: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)


class WebRunFailure(ContractModel):
    code: str = Field(min_length=1)
    message: str | None = None
    retryable: bool | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)


class WebRunRecord(ContractModel):
    run_id: str = Field(min_length=1)
    run_status: WebRunStatus
    result_state: WebResultState | None = None
    cancel_requested: bool = False
    created_at: datetime
    updated_at: datetime
    input: WebRunInput
    prompts: list[WebRunPrompt] = Field(default_factory=list)
    eta_seconds: int | None = Field(default=None, ge=0)
    failure: WebRunFailure | None = None


class WebRunProgressSnapshot(ContractModel):
    completed_prompts: int = Field(ge=0)
    failed_prompts: int = Field(ge=0)
    total_prompts: int = Field(ge=0)
    current_prompt_id: str | None = None
    eta_seconds: int | None = Field(default=None, ge=0)


class WebRunSnapshot(ContractModel):
    run_id: str = Field(min_length=1)
    run_status: WebRunStatus
    result_state: WebResultState | None = None
    cancel_requested: bool = False
    created_at: datetime
    updated_at: datetime
    input: WebRunInput
    progress: WebRunProgressSnapshot
    prompts: list[WebRunPrompt] = Field(default_factory=list)
    failure: WebRunFailure | None = None
