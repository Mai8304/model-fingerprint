from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

PromptFamily = Literal[
    "style_brief",
    "strict_format",
    "minimal_diff",
    "structured_extraction",
    "retrieval",
]

RiskLevel = Literal["low", "medium", "high"]
MessageRole = Literal["system", "user", "assistant"]
ResponseFormat = Literal["text", "json_object"]
ReasoningMode = Literal["ignore", "capture_if_available", "require_visible"]
CapabilityId = Literal[
    "chat_completions",
    "json_object_response",
    "visible_reasoning",
]
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
