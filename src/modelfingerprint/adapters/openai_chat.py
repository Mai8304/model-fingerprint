from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from modelfingerprint.contracts.prompt import PromptDefinition


@dataclass(frozen=True)
class ChatCompletionResult:
    content: str
    input_tokens: int
    output_tokens: int
    total_tokens: int


class ChatCompletionTransport(Protocol):
    def complete(self, prompt: PromptDefinition) -> ChatCompletionResult:
        """Return a chat-style completion result for one prompt."""


class OpenAIChatAdapter:
    def complete(self, prompt: PromptDefinition) -> ChatCompletionResult:
        raise NotImplementedError(
            "Live OpenAI-compatible transport is optional and not wired in default tests."
        )
