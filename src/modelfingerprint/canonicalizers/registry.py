from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.canonicalizers.base import (
    CanonicalizationError,
    CanonicalizerHandler,
    CanonicalizerResult,
)
from modelfingerprint.canonicalizers.tolerant_json import canonicalize_tolerant_json
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
            "tolerant_json_v3": canonicalize_tolerant_json,
        }
    )
