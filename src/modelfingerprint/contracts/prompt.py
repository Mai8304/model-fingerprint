from __future__ import annotations

from pydantic import Field

from modelfingerprint.contracts._common import (
    CanonicalizerId,
    CapabilityId,
    ContractModel,
    ExtractorId,
    MessageRole,
    OutputContractId,
    Probability,
    PromptFamily,
    PromptId,
    ReasoningMode,
    ResponseFormat,
    RiskLevel,
    SuiteId,
)


class PromptMessage(ContractModel):
    role: MessageRole
    content: str = Field(min_length=1)


class OutputContract(ContractModel):
    id: OutputContractId
    canonicalizer: CanonicalizerId


class GenerationSpec(ContractModel):
    temperature: float = Field(ge=0.0)
    top_p: float = Field(gt=0.0, le=1.0)
    max_output_tokens: int = Field(ge=1)
    response_format: ResponseFormat
    reasoning_mode: ReasoningMode


class PromptExtractors(ContractModel):
    answer: ExtractorId
    score: ExtractorId | None = None
    reasoning: ExtractorId | None = None
    transport: ExtractorId | None = None


class PromptEvaluation(ContractModel):
    reference: dict[str, object] = Field(min_length=1)


class PromptDefinition(ContractModel):
    id: PromptId
    name: str = Field(min_length=1)
    family: PromptFamily
    intent: str = Field(min_length=1)
    messages: list[PromptMessage] = Field(min_length=1)
    generation: GenerationSpec
    output_contract: OutputContract
    extractors: PromptExtractors
    evaluation: PromptEvaluation | None = None
    required_capabilities: list[CapabilityId] = Field(min_length=1)
    weight_hint: Probability = 1.0
    tags: list[str] = Field(default_factory=list)
    risk_level: RiskLevel

    @property
    def extractor(self) -> ExtractorId:
        """Backwards-compatible accessor for the primary answer extractor."""
        return self.extractors.answer

    @property
    def template(self) -> str:
        """Backwards-compatible accessor for rendering legacy prompt text."""
        return "\n\n".join(message.content for message in self.messages)


class SuiteDefinition(ContractModel):
    id: SuiteId
    name: str = Field(min_length=1)
    prompt_ids: list[PromptId] = Field(min_length=1)
    description: str | None = None
