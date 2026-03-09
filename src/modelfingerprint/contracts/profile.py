from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator

from modelfingerprint.contracts._common import (
    ContractModel,
    Probability,
    PromptId,
    SuiteId,
)


class NumericFeatureSummary(ContractModel):
    kind: Literal["numeric"]
    median: float
    mad: float = Field(ge=0.0)


class BooleanFeatureSummary(ContractModel):
    kind: Literal["boolean"]
    p_true: Probability


class EnumFeatureSummary(ContractModel):
    kind: Literal["enum"]
    distribution: dict[str, Probability] = Field(min_length=1)

    @field_validator("distribution")
    @classmethod
    def validate_distribution(cls, value: dict[str, float]) -> dict[str, float]:
        total = sum(value.values())
        if total <= 0.0:
            raise ValueError("distribution must have positive total mass")
        return value


FeatureSummary = Annotated[
    NumericFeatureSummary | BooleanFeatureSummary | EnumFeatureSummary,
    Field(discriminator="kind"),
]


class ProfilePromptSummary(ContractModel):
    prompt_id: PromptId
    weight: Probability = 1.0
    features: dict[str, FeatureSummary] = Field(min_length=1)


class ProfileArtifact(ContractModel):
    model_id: str = Field(min_length=1)
    suite_id: SuiteId
    sample_count: int = Field(gt=0)
    prompts: list[ProfilePromptSummary] = Field(min_length=1)
