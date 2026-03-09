from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml

from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import CanonicalizedOutput, NormalizedCompletion
from modelfingerprint.extractors.abstention import extract_abstention, score_abstention
from modelfingerprint.extractors.base import (
    ExtractorDescriptor,
    ExtractorHandler,
    ExtractorValidationError,
    FeatureMap,
    RegisteredExtractor,
    ScoreExtractorHandler,
    SurfaceExtractorInput,
    ensure_json_serializable,
)
from modelfingerprint.extractors.completion_metadata import extract_completion_metadata
from modelfingerprint.extractors.context_retrieval import (
    extract_context_retrieval,
    score_context_retrieval,
)
from modelfingerprint.extractors.evidence_grounding import (
    extract_evidence_grounding,
    score_evidence_grounding,
)
from modelfingerprint.extractors.minimal_diff import extract_minimal_diff
from modelfingerprint.extractors.reasoning_trace import extract_reasoning_trace
from modelfingerprint.extractors.representation_alignment import (
    extract_representation_alignment,
    score_representation_alignment,
)
from modelfingerprint.extractors.retrieval import extract_retrieval
from modelfingerprint.extractors.state_tracking import (
    extract_state_tracking,
    score_state_tracking,
)
from modelfingerprint.extractors.strict_format import extract_strict_format
from modelfingerprint.extractors.structured_extraction import extract_structured_extraction
from modelfingerprint.extractors.style_brief import extract_style_brief
from modelfingerprint.extractors.surface_contract import extract_surface_contract

SURFACE_EXTRACTOR_NAME = "surface_contract_v1"


class ExtractorRegistry:
    def __init__(
        self,
        descriptors: dict[str, ExtractorDescriptor],
        handlers: Mapping[str, ExtractorHandler],
        score_handlers: Mapping[str, ScoreExtractorHandler] | None = None,
    ) -> None:
        self._descriptors = descriptors
        self._handlers = dict(handlers)
        self._score_handlers = dict(score_handlers or {})

    @classmethod
    def from_directory(
        cls,
        directory: Path,
        handlers: Mapping[str, ExtractorHandler],
        score_handlers: Mapping[str, ScoreExtractorHandler] | None = None,
    ) -> ExtractorRegistry:
        descriptors: dict[str, ExtractorDescriptor] = {}

        for path in sorted(directory.glob("*.yaml")):
            descriptor = ExtractorDescriptor.model_validate(
                yaml.safe_load(path.read_text(encoding="utf-8"))
            )
            descriptors[descriptor.name] = descriptor

        return cls(
            descriptors=descriptors,
            handlers=handlers,
            score_handlers=score_handlers,
        )

    def get(self, name: str) -> RegisteredExtractor:
        descriptor = self._descriptors.get(name)
        handler = self._handlers.get(name)

        if descriptor is None or handler is None:
            raise ExtractorValidationError(f"unknown extractor: {name}")

        return RegisteredExtractor(descriptor=descriptor, handler=handler)

    def get_for_prompt(self, prompt: PromptDefinition) -> RegisteredExtractor:
        return self.get(prompt.extractor)

    def has(self, name: str) -> bool:
        return name in self._descriptors and (
            name in self._handlers or name in self._score_handlers
        )

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

    def extract_score(
        self,
        prompt: PromptDefinition,
        canonical_output: CanonicalizedOutput,
    ) -> FeatureMap:
        if prompt.extractors.score is None:
            return {}
        descriptor = self._descriptors.get(prompt.extractors.score)
        handler = self._score_handlers.get(prompt.extractors.score)
        if descriptor is None or handler is None:
            raise ExtractorValidationError(f"unknown score extractor: {prompt.extractors.score}")
        feature_map = handler(prompt, canonical_output)
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
        "evidence_grounding_v1": extract_evidence_grounding,
        "context_retrieval_v1": extract_context_retrieval,
        "abstention_v1": extract_abstention,
        "state_tracking_v1": extract_state_tracking,
        "representation_alignment_v1": extract_representation_alignment,
        "reasoning_trace_v1": extract_reasoning_trace,
        "completion_metadata_v1": extract_completion_metadata,
        SURFACE_EXTRACTOR_NAME: extract_surface_contract,
    }
    score_handlers = {
        "evidence_grounding_score_v1": score_evidence_grounding,
        "context_retrieval_score_v1": score_context_retrieval,
        "abstention_score_v1": score_abstention,
        "state_tracking_score_v1": score_state_tracking,
        "representation_alignment_score_v1": score_representation_alignment,
    }
    return ExtractorRegistry.from_directory(
        directory,
        handlers=handlers,
        score_handlers=score_handlers,
    )
