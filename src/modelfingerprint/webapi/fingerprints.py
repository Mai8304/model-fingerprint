from __future__ import annotations

from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.webapi.fingerprint_chain import (
    WEB_FINGERPRINT_SUITE_ID,
    load_web_fingerprint_chain,
)
from modelfingerprint.webapi.contracts import WebFingerprintModel

LABEL_OVERRIDES = {
    "deepseek-chat": "DeepSeek Chat",
    "glm-4.7": "GLM-4.7",
    "glm-5": "GLM-5",
    "gpt-4.1-mini": "GPT-4.1 Mini",
    "gpt-5.3-chat": "GPT-5.3 Chat",
    "gpt-5.3-codex": "GPT-5.3 Codex",
    "gpt-5.4": "GPT-5.4",
    "minimax-m2.5": "MiniMax M2.5",
}


def list_fingerprint_models(paths: RepositoryPaths) -> list[WebFingerprintModel]:
    chain = load_web_fingerprint_chain(paths)
    items: list[WebFingerprintModel] = []
    for profile in chain.profiles:
        items.append(
            WebFingerprintModel(
                id=profile.model_id,
                label=display_model_label(profile.model_id),
                suite_id=profile.suite_id,
                available=True,
                image_generation=_capability_summary(profile, "image_generation"),
                vision_understanding=_capability_summary(profile, "vision_understanding"),
            )
        )

    return items


def display_model_label(model_id: str) -> str:
    if model_id in LABEL_OVERRIDES:
        return LABEL_OVERRIDES[model_id]

    return " ".join(
        part.upper() if part.isupper() else part.title()
        for part in model_id.split("-")
    )


def _capability_summary(profile: ProfileArtifact, capability: str):
    capability_profile = profile.capability_profile
    if capability_profile is None:
        return None
    distribution = capability_profile.capabilities.get(capability)
    if distribution is None:
        return None
    status, confidence = max(
        distribution.distribution.items(),
        key=lambda item: (item[1], item[0]),
    )
    return {
        "status": status,
        "confidence": confidence,
    }
