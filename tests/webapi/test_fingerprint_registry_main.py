from __future__ import annotations

from pathlib import Path

from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.webapi.fingerprints import list_fingerprint_models

ROOT = Path(__file__).resolve().parents[2]


def test_main_repo_v32_registry_exposes_expected_models() -> None:
    items = list_fingerprint_models(RepositoryPaths(root=ROOT))

    assert [item.id for item in items] == [
        "claude-haiku-4.5",
        "claude-opus-4.1",
        "claude-opus-4.6",
        "claude-sonnet-4.6",
        "deepseek-chat",
        "gemini-2.5-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-3.1-pro-preview",
        "glm-4.7",
        "glm-5",
        "gpt-5.3-chat",
        "gpt-5.3-codex",
        "gpt-5.4",
        "kimi-k2-thinking",
        "kimi-k2.5",
        "minimax-m2.5",
        "nano-banana",
        "nano-banana-pro",
    ]
    assert [item.label for item in items] == [
        "Claude Haiku 4.5",
        "Claude Opus 4.1",
        "Claude Opus 4.6",
        "Claude Sonnet 4.6",
        "DeepSeek Chat",
        "Gemini 2.5 Flash Lite",
        "Gemini 3 Flash Preview",
        "Gemini 3 Pro Preview",
        "Gemini 3.1 Pro Preview",
        "GLM-4.7",
        "GLM-5",
        "GPT-5.3 Chat",
        "GPT-5.3 Codex",
        "GPT-5.4",
        "Kimi K2 Thinking",
        "Kimi K2.5",
        "MiniMax M2.5",
        "Nano Banana",
        "Nano Banana Pro",
    ]
    nano_banana = next(item for item in items if item.id == "nano-banana")
    assert nano_banana.image_generation is not None
    assert nano_banana.image_generation.status == "supported"
    assert nano_banana.vision_understanding is not None
    assert nano_banana.vision_understanding.status == "supported"
