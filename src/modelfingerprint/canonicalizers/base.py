from __future__ import annotations

from collections.abc import Callable

from modelfingerprint.contracts.run import CanonicalizationEvent, CanonicalizedOutput

CanonicalizerResult = tuple[CanonicalizedOutput, list[CanonicalizationEvent]]
CanonicalizerHandler = Callable[[str], CanonicalizerResult]


class CanonicalizationError(ValueError):
    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

