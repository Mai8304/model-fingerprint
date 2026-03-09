from __future__ import annotations

from pydantic import Field

from modelfingerprint.contracts._common import (
    ContractModel,
    ExtractorId,
    OutputType,
    PromptFamily,
    PromptId,
    Probability,
    RiskLevel,
)


class PromptVariable(ContractModel):
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool = True


class OutputContract(ContractModel):
    type: OutputType


class PromptDefinition(ContractModel):
    id: PromptId
    name: str = Field(min_length=1)
    family: PromptFamily
    intent: str = Field(min_length=1)
    template: str = Field(min_length=1)
    variables: list[PromptVariable] = Field(default_factory=list)
    output_contract: OutputContract
    extractor: ExtractorId
    weight_hint: Probability = 1.0
    tags: list[str] = Field(default_factory=list)
    risk_level: RiskLevel
