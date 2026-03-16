from __future__ import annotations

import json

from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.webapi.contracts import WebFingerprintModel

WEB_FINGERPRINT_SUITE_ID = "fingerprint-suite-v32"

LABEL_OVERRIDES = {
    "deepseek-chat": "DeepSeek Chat",
    "glm-5": "GLM-5",
    "gpt-4.1-mini": "GPT-4.1 Mini",
}


def list_fingerprint_models(paths: RepositoryPaths) -> list[WebFingerprintModel]:
    profile_dir = paths.profiles_dir / WEB_FINGERPRINT_SUITE_ID
    if not profile_dir.exists():
        return []

    items: list[WebFingerprintModel] = []
    for path in sorted(profile_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        profile = ProfileArtifact.model_validate(payload)
        items.append(
            WebFingerprintModel(
                id=profile.model_id,
                label=display_model_label(profile.model_id),
                suite_id=profile.suite_id,
                available=True,
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
