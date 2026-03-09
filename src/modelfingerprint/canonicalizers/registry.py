from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.canonicalizers.base import (
    CanonicalizationError,
    CanonicalizerHandler,
    CanonicalizerResult,
)
from modelfingerprint.canonicalizers.plain_text import canonicalize_plain_text
from modelfingerprint.canonicalizers.retrieval import canonicalize_retrieval
from modelfingerprint.canonicalizers.strict_json import canonicalize_strict_json
from modelfingerprint.canonicalizers.structured_extraction import (
    canonicalize_structured_extraction,
)
from modelfingerprint.canonicalizers.tagged_text import canonicalize_tagged_text
from modelfingerprint.contracts.prompt import PromptDefinition


class CanonicalizerRegistry:
    def __init__(self, handlers: Mapping[str, CanonicalizerHandler]) -> None:
        self._handlers = dict(handlers)

    def canonicalize(
        self,
        prompt: PromptDefinition,
        raw_output: str,
    ) -> CanonicalizerResult:
        handler = self._handlers.get(prompt.output_contract.canonicalizer)
        if handler is None:
            raise CanonicalizationError(
                code="unknown_canonicalizer",
                message=f"unknown canonicalizer: {prompt.output_contract.canonicalizer}",
            )
        return handler(raw_output)


def build_default_registry() -> CanonicalizerRegistry:
    return CanonicalizerRegistry(
        {
            "plain_text_v2": canonicalize_plain_text,
            "strict_json_v2": canonicalize_strict_json,
            "tagged_text_v2": canonicalize_tagged_text,
            "structured_extraction_v2": canonicalize_structured_extraction,
            "retrieval_v2": canonicalize_retrieval,
        }
    )
