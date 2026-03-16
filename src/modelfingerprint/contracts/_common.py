from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

PromptFamily = Literal[
    "evidence_grounding",
    "context_retrieval",
    "abstention",
    "state_tracking",
    "representation_alignment",
    "boundary_decision",
    "mention_classification",
    "selection_boundary",
]
ExtractorFamily = PromptFamily | Literal["strict_format"]

RiskLevel = Literal["low", "medium", "high"]
MessageRole = Literal["system", "user", "assistant"]
ResponseFormat = Literal["text", "json_object"]
ReasoningMode = Literal["ignore", "capture_if_available", "require_visible"]
CapabilityId = Literal[
    "chat_completions",
    "json_object_response",
    "visible_reasoning",
    "json_schema_response",
    "function_calling",
    "tool_calling",
]
ProbeCapabilityId = Literal[
    "thinking",
    "tools",
    "streaming",
    "image",
    "image_generation",
    "vision_understanding",
]
ProbeCapabilityStatus = Literal[
    "supported",
    "accepted_but_ignored",
    "unsupported",
    "insufficient_evidence",
]
RuntimeExecutionClass = Literal["thinking", "non_thinking"]
OutputContractId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+_v[1-9]\d*$")]
CanonicalizerId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+_v[1-9]\d*$")]
SuiteId = Annotated[
    str,
    StringConstraints(pattern=r"^(research-set|fingerprint-suite|quick-check)-v[1-9]\d*$"),
]
PromptId = Annotated[str, StringConstraints(pattern=r"^p\d{3}$")]
ExtractorId = Annotated[str, StringConstraints(pattern=r"^[a-z_]+_v[1-9]\d*$")]
FeaturePrimitive = bool | int | float | str


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Probability = Annotated[float, Field(ge=0.0, le=1.0)]
