from __future__ import annotations

from pathlib import Path

import yaml

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.extractors.base import (
    ExtractorDescriptor,
    ExtractorHandler,
    ExtractorValidationError,
    FeatureMap,
    RegisteredExtractor,
    ensure_json_serializable,
)


class ExtractorRegistry:
    def __init__(
        self,
        descriptors: dict[str, ExtractorDescriptor],
        handlers: dict[str, ExtractorHandler],
    ) -> None:
        self._descriptors = descriptors
        self._handlers = handlers

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        handlers: dict[str, ExtractorHandler],
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

    def extract(self, prompt: PromptDefinition, raw_output: str) -> FeatureMap:
        resolved = self.get_for_prompt(prompt)
        feature_map = resolved.handler(raw_output)
        ensure_json_serializable(feature_map)
        return feature_map
