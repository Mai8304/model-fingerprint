from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import Field

from modelfingerprint.contracts._common import ContractModel, FeaturePrimitive, PromptFamily


FeatureMap = dict[str, FeaturePrimitive]
ExtractorHandler = Callable[[str], FeatureMap]


class ExtractorValidationError(ValueError):
    """Raised when extractor descriptors or outputs are invalid."""


class ExtractorDescriptor(ContractModel):
    name: str = Field(min_length=1)
    family: PromptFamily
    version: int = Field(gt=0)
    features: list[str] = Field(min_length=1)


@dataclass(frozen=True)
class RegisteredExtractor:
    descriptor: ExtractorDescriptor
    handler: ExtractorHandler


def ensure_json_serializable(feature_map: FeatureMap) -> None:
    try:
        json.dumps(feature_map)
    except TypeError as exc:
        raise ExtractorValidationError("extractor outputs must be JSON-serializable") from exc
