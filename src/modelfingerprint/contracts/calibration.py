from __future__ import annotations

from pydantic import model_validator

from modelfingerprint.contracts._common import ContractModel, Probability, SuiteId


class CalibrationThresholds(ContractModel):
    match: Probability
    suspicious: Probability
    unknown: Probability
    margin: Probability
    consistency: Probability


class SimilarityStats(ContractModel):
    mean: Probability
    p05: Probability
    p50: Probability
    p95: Probability

    @model_validator(mode="after")
    def validate_ordering(self) -> SimilarityStats:
        if not (self.p05 <= self.p50 <= self.p95):
            raise ValueError("expected p05 <= p50 <= p95")
        return self


class CalibrationArtifact(ContractModel):
    suite_id: SuiteId
    thresholds: CalibrationThresholds
    same_model_stats: SimilarityStats
    cross_model_stats: SimilarityStats
