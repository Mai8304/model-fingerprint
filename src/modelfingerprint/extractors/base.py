from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import Field, model_validator

from modelfingerprint.contracts._common import (
    ContractModel,
    ExtractorFamily,
    FeaturePrimitive,
)
from modelfingerprint.contracts.run import CanonicalizationEvent, CanonicalizedOutput

FeatureMap = dict[str, FeaturePrimitive]
ExtractorHandler = Callable[[object], FeatureMap]
ScoreExtractorHandler = Callable[[object, CanonicalizedOutput], FeatureMap]


@dataclass(frozen=True)
class SurfaceExtractorInput:
    raw_output: str
    canonical_output: CanonicalizedOutput
    canonicalization_events: list[CanonicalizationEvent] = field(default_factory=list)


class ExtractorValidationError(ValueError):
    """Raised when extractor descriptors or outputs are invalid."""


class ExtractorDescriptor(ContractModel):
    name: str = Field(min_length=1)
    family: ExtractorFamily
    version: int = Field(gt=0)
    features: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_features(self) -> ExtractorDescriptor:
        if len(self.features) != len(set(self.features)):
            raise ValueError("extractor features must be unique")
        return self


@dataclass(frozen=True)
class RegisteredExtractor:
    descriptor: ExtractorDescriptor
    handler: ExtractorHandler


def ensure_json_serializable(feature_map: FeatureMap) -> None:
    try:
        json.dumps(feature_map)
    except TypeError as exc:
        raise ExtractorValidationError("extractor outputs must be JSON-serializable") from exc
