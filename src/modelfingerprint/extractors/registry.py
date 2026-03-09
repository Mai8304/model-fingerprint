from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput, NormalizedCompletion
from modelfingerprint.extractors.base import (
    ExtractorDescriptor,
    ExtractorHandler,
    ExtractorValidationError,
    FeatureMap,
    RegisteredExtractor,
    SurfaceExtractorInput,
    ensure_json_serializable,
)
from modelfingerprint.extractors.minimal_diff import extract_minimal_diff
from modelfingerprint.extractors.retrieval import extract_retrieval
from modelfingerprint.extractors.strict_format import extract_strict_format
from modelfingerprint.extractors.structured_extraction import extract_structured_extraction
from modelfingerprint.extractors.style_brief import extract_style_brief

SURFACE_EXTRACTOR_NAME = "surface_contract_v1"


class ExtractorRegistry:
    def __init__(
        self,
        descriptors: dict[str, ExtractorDescriptor],
        handlers: Mapping[str, ExtractorHandler],
    ) -> None:
        self._descriptors = descriptors
        self._handlers = dict(handlers)

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        handlers: Mapping[str, ExtractorHandler],
    ) -> ExtractorRegistry:
        descriptors: dict[str, ExtractorDescriptor] = {}

        for path in sorted(directory.glob("*.yaml")):
            descriptor = ExtractorDescriptor.model_validate(
                yaml.safe_load(path.read_text(encoding="utf-8"))
            )
            descriptors[descriptor.name] = descriptor

        return cls(descriptors=descriptors, handlers=handlers)

    def get(self, name: str) -> RegisteredExtractor:
        descriptor = self._descriptors.get(name)
        handler = self._handlers.get(name)

        if descriptor is None or handler is None:
            raise ExtractorValidationError(f"unknown extractor: {name}")

        return RegisteredExtractor(descriptor=descriptor, handler=handler)

    def get_for_prompt(self, prompt: PromptDefinition) -> RegisteredExtractor:
        return self.get(prompt.extractor)

    def has(self, name: str) -> bool:
        return name in self._descriptors and name in self._handlers

    def extract_answer(
        self,
        prompt: PromptDefinition,
        canonical_output: CanonicalizedOutput,
    ) -> FeatureMap:
        resolved = self.get(prompt.extractors.answer)
        feature_map = resolved.handler(canonical_output)
        ensure_json_serializable(feature_map)
        return feature_map

    def extract_reasoning(
        self,
        prompt: PromptDefinition,
        reasoning_text: str,
    ) -> FeatureMap:
        if prompt.extractors.reasoning is None:
            return {}
        resolved = self.get(prompt.extractors.reasoning)
        feature_map = resolved.handler(reasoning_text)
        ensure_json_serializable(feature_map)
        return feature_map

    def extract_transport(
        self,
        prompt: PromptDefinition,
        completion: NormalizedCompletion,
    ) -> FeatureMap:
        if prompt.extractors.transport is None:
            return {}
        resolved = self.get(prompt.extractors.transport)
        feature_map = resolved.handler(completion)
        ensure_json_serializable(feature_map)
        return feature_map

    def extract_surface(
        self,
        *,
        raw_output: str,
        canonical_output: CanonicalizedOutput,
    ) -> FeatureMap:
        resolved = self.get(SURFACE_EXTRACTOR_NAME)
        feature_map = resolved.handler(
            SurfaceExtractorInput(raw_output=raw_output, canonical_output=canonical_output)
        )
        ensure_json_serializable(feature_map)
        return feature_map


def build_default_registry(directory: Path) -> ExtractorRegistry:
    handlers = {
        "style_brief_v1": extract_style_brief,
        "strict_format_v1": extract_strict_format,
        "minimal_diff_v1": extract_minimal_diff,
        "structured_extraction_v1": extract_structured_extraction,
        "retrieval_v1": extract_retrieval,
    }
    return ExtractorRegistry.from_directory(directory, handlers=handlers)
