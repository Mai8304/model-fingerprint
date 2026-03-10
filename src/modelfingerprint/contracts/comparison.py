from __future__ import annotations

from typing import Literal

from pydantic import Field

from modelfingerprint.contracts._common import (
    ContractModel,
    Probability,
    ProbeCapabilityId,
    ProbeCapabilityStatus,
    PromptId,
    SuiteId,
)

ComparisonProtocolStatus = Literal[
    "compatible",
    "insufficient_evidence",
    "incompatible_protocol",
]
ComparisonVerdict = Literal[
    "match",
    "suspicious",
    "mismatch",
    "unknown",
    "insufficient_evidence",
    "incompatible_protocol",
]
PromptRunStatus = Literal[
    "completed",
    "timeout",
    "transport_error",
    "unsupported_capability",
    "truncated",
    "invalid_response",
    "canonicalization_error",
]


class ComparisonSummary(ContractModel):
    top1_model: str = Field(min_length=1)
    top1_similarity: Probability
    top2_model: str = Field(min_length=1)
    top2_similarity: Probability
    margin: float = Field(ge=0.0)
    claimed_model_similarity: Probability | None = None
    consistency: Probability
    verdict: ComparisonVerdict


class ComparisonDimensions(ContractModel):
    content_similarity: Probability | None = None
    capability_similarity: Probability | None = None
    answer_similarity: Probability | None = None
    reasoning_similarity: Probability | None = None
    transport_similarity: Probability | None = None
    surface_similarity: Probability | None = None


class ComparisonCoverage(ContractModel):
    answer_coverage_ratio: Probability
    reasoning_coverage_ratio: Probability
    capability_coverage_ratio: Probability
    protocol_status: ComparisonProtocolStatus


class ComparisonDiagnostics(ContractModel):
    protocol_issues: list[str] = Field(default_factory=list)
    hard_mismatches: list[str] = Field(default_factory=list)


class CandidateComparison(ContractModel):
    model_id: str = Field(min_length=1)
    overall_similarity: Probability
    content_similarity: Probability | None = None
    capability_similarity: Probability | None = None
    answer_similarity: Probability | None = None
    reasoning_similarity: Probability | None = None
    transport_similarity: Probability | None = None
    surface_similarity: Probability | None = None
    consistency: Probability
    answer_coverage_ratio: Probability
    reasoning_coverage_ratio: Probability
    capability_coverage_ratio: Probability
    protocol_status: ComparisonProtocolStatus
    protocol_issues: list[str] = Field(default_factory=list)
    hard_mismatches: list[str] = Field(default_factory=list)
    prompt_scores: dict[PromptId, Probability] = Field(default_factory=dict)


class PromptComparisonBreakdown(ContractModel):
    prompt_id: PromptId
    status: PromptRunStatus
    similarity: Probability | None = None
    scoreable: bool
    error_kind: str | None = None
    error_message: str | None = None


class CapabilityComparisonBreakdown(ContractModel):
    capability: ProbeCapabilityId
    weight: Probability
    observed_status: ProbeCapabilityStatus | None = None
    expected_distribution: dict[ProbeCapabilityStatus, Probability] = Field(default_factory=dict)
    similarity: Probability | None = None


class ComparisonThresholdsUsed(ContractModel):
    match: Probability
    suspicious: Probability
    unknown: Probability
    margin: Probability
    consistency: Probability
    answer_min: Probability
    reasoning_min: Probability


class ComparisonArtifact(ContractModel):
    schema_version: Literal["comparison.v1"]
    suite_id: SuiteId
    run_id: str = Field(min_length=1)
    target_label: str = Field(min_length=1)
    claimed_model: str | None = None
    calibration_id: str = Field(min_length=1)
    summary: ComparisonSummary
    dimensions: ComparisonDimensions
    coverage: ComparisonCoverage
    diagnostics: ComparisonDiagnostics
    candidates: list[CandidateComparison] = Field(min_length=1)
    prompt_breakdown: list[PromptComparisonBreakdown] = Field(default_factory=list)
    capability_breakdown: list[CapabilityComparisonBreakdown] = Field(default_factory=list)
    thresholds_used: ComparisonThresholdsUsed
