from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from modelfingerprint.contracts._common import (
    ContractModel,
    Probability,
    ProbeCapabilityId,
    ProbeCapabilityStatus,
    SuiteId,
)
from modelfingerprint.contracts.comparison import ComparisonVerdict

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

WebRunStageId = Literal[
    "config_validation",
    "endpoint_resolution",
    "capability_probe",
    "prompt_execution",
    "comparison",
]

WebRunStageStatus = Literal[
    "pending",
    "running",
    "completed",
    "failed",
]

WebProtocolStatus = Literal[
    "compatible",
    "insufficient_evidence",
    "incompatible_protocol",
]


class WebFingerprintCapabilitySummary(ContractModel):
    status: ProbeCapabilityStatus | None = None
    confidence: Probability | None = None


class WebFingerprintModel(ContractModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    suite_id: SuiteId
    available: bool
    image_generation: WebFingerprintCapabilitySummary | None = None
    vision_understanding: WebFingerprintCapabilitySummary | None = None


class WebRunInput(ContractModel):
    base_url: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    fingerprint_model_id: str = Field(min_length=1)


class WebRunStage(ContractModel):
    id: WebRunStageId
    status: WebRunStageStatus
    message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class WebRunPrompt(ContractModel):
    prompt_id: str = Field(min_length=1)
    status: WebPromptStatus
    elapsed_seconds: int | None = Field(default=None, ge=0)
    elapsed_ms: int | None = Field(default=None, ge=0)
    summary_code: str | None = None
    error_code: str | None = None
    error_kind: str | None = None
    error_detail: str | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    first_byte_ms: int | None = Field(default=None, ge=0)
    bytes_received: int | None = Field(default=None, ge=0)
    finish_reason: str | None = None
    parse_status: str | None = None
    answer_present: bool | None = None
    reasoning_present: bool | None = None
    scoreable: bool | None = None


class WebRunFailure(ContractModel):
    code: str = Field(min_length=1)
    message: str | None = None
    retryable: bool | None = None
    http_status: int | None = Field(default=None, ge=100, le=599)
    field: str | None = None


class WebRunResultFingerprint(ContractModel):
    id: str = Field(min_length=1)
    label: str = Field(min_length=1)


class WebRunResultSummary(ContractModel):
    similarity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_low: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_high: float | None = Field(default=None, ge=0.0, le=1.0)
    range_gap: float | None = Field(default=None, ge=0.0)
    in_confidence_range: bool | None = None
    top_candidate_model_id: str | None = None
    top_candidate_label: str | None = None
    top_candidate_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    top2_candidate_model_id: str | None = None
    top2_candidate_label: str | None = None
    top2_candidate_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    margin: float | None = Field(default=None, ge=0.0)
    consistency: float | None = Field(default=None, ge=0.0, le=1.0)


class WebRunResultCandidate(ContractModel):
    model_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    similarity: float = Field(ge=0.0, le=1.0)
    content_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    capability_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    consistency: float | None = Field(default=None, ge=0.0, le=1.0)
    answer_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    capability_coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    protocol_status: WebProtocolStatus | None = None
    protocol_issues: list[str] = Field(default_factory=list)
    hard_mismatches: list[str] = Field(default_factory=list)


class WebRunResultDimensions(ContractModel):
    content_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    capability_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    answer_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    reasoning_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    transport_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    surface_similarity: float | None = Field(default=None, ge=0.0, le=1.0)


class WebRunResultCoverage(ContractModel):
    answer_coverage_ratio: float = Field(ge=0.0, le=1.0)
    reasoning_coverage_ratio: float = Field(ge=0.0, le=1.0)
    capability_coverage_ratio: float = Field(ge=0.0, le=1.0)
    protocol_status: WebProtocolStatus


class WebRunResultPromptBreakdown(ContractModel):
    prompt_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    scoreable: bool
    error_kind: str | None = None
    error_message: str | None = None


class WebRunResultCapabilityComparison(ContractModel):
    capability: ProbeCapabilityId
    observed_status: ProbeCapabilityStatus | None = None
    expected_status: ProbeCapabilityStatus | None = None
    is_consistent: bool | None = None


class WebRunResultThresholds(ContractModel):
    match: float = Field(ge=0.0, le=1.0)
    suspicious: float = Field(ge=0.0, le=1.0)
    unknown: float = Field(ge=0.0, le=1.0)
    margin: float = Field(ge=0.0)
    consistency: float = Field(ge=0.0, le=1.0)
    answer_min: float = Field(ge=0.0, le=1.0)
    reasoning_min: float = Field(ge=0.0, le=1.0)


class WebRunResultDiagnostics(ContractModel):
    protocol_status: WebProtocolStatus
    protocol_issues: list[str] = Field(default_factory=list)
    hard_mismatches: list[str] = Field(default_factory=list)
    blocking_reasons: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class WebRunResult(ContractModel):
    run_id: str = Field(min_length=1)
    result_state: WebResultState
    selected_fingerprint: WebRunResultFingerprint
    completed_prompts: int = Field(ge=0)
    total_prompts: int = Field(ge=0)
    verdict: ComparisonVerdict | None = None
    summary: WebRunResultSummary | None = None
    selected_candidate: WebRunResultCandidate | None = None
    candidates: list[WebRunResultCandidate] = Field(default_factory=list)
    dimensions: WebRunResultDimensions | None = None
    coverage: WebRunResultCoverage | None = None
    diagnostics: WebRunResultDiagnostics
    prompt_breakdown: list[WebRunResultPromptBreakdown] = Field(default_factory=list)
    capability_comparisons: list[WebRunResultCapabilityComparison] = Field(default_factory=list)
    thresholds_used: WebRunResultThresholds | None = None


class WebRunRecord(ContractModel):
    run_id: str = Field(min_length=1)
    run_status: WebRunStatus
    result_state: WebResultState | None = None
    cancel_requested: bool = False
    created_at: datetime
    updated_at: datetime
    input: WebRunInput
    current_stage_id: WebRunStageId | None = None
    current_stage_message: str | None = None
    stages: list[WebRunStage] = Field(default_factory=list)
    prompts: list[WebRunPrompt] = Field(default_factory=list)
    eta_seconds: int | None = Field(default=None, ge=0)
    failure: WebRunFailure | None = None
    result: WebRunResult | None = None


class WebRunProgressSnapshot(ContractModel):
    completed_prompts: int = Field(ge=0)
    failed_prompts: int = Field(ge=0)
    total_prompts: int = Field(ge=0)
    current_prompt_id: str | None = None
    current_prompt_index: int | None = Field(default=None, ge=1)
    eta_seconds: int | None = Field(default=None, ge=0)


class WebRunSnapshot(ContractModel):
    run_id: str = Field(min_length=1)
    run_status: WebRunStatus
    result_state: WebResultState | None = None
    cancel_requested: bool = False
    created_at: datetime
    updated_at: datetime
    input: WebRunInput
    current_stage_id: WebRunStageId | None = None
    current_stage_message: str | None = None
    stages: list[WebRunStage] = Field(default_factory=list)
    progress: WebRunProgressSnapshot
    prompts: list[WebRunPrompt] = Field(default_factory=list)
    failure: WebRunFailure | None = None
