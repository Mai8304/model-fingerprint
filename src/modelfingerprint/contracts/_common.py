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
OutputType = Literal["plain_text", "json", "tagged_text"]
SuiteId = Annotated[
    str,
    StringConstraints(pattern=r"^(candidate-pool|default|screening)-v[1-9]\d*$"),
]
PromptId = Annotated[str, StringConstraints(pattern=r"^p\d{3}$")]
ExtractorId = Annotated[str, StringConstraints(pattern=r"^[a-z_]+_v[1-9]\d*$")]
FeaturePrimitive = bool | int | float | str


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Probability = Annotated[float, Field(ge=0.0, le=1.0)]
