from __future__ import annotations

from pathlib import Path

import yaml

from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.prompt import PromptDefinition

KNOWN_DIALECT_IDS = frozenset({"openai_chat_v1"})

CAPABILITY_FIELD_MAP = {
    "chat_completions": None,
    "json_object_response": "supports_json_object_response",
    "visible_reasoning": "exposes_reasoning_text",
}


class EndpointProfileValidationError(ValueError):
    """Raised when endpoint-profile files violate repository invariants."""


def load_endpoint_profiles(directory: Path) -> dict[str, EndpointProfile]:
    profiles: dict[str, EndpointProfile] = {}

    for path in sorted(directory.rglob("*.yaml")):
        profile = EndpointProfile.model_validate(_read_yaml(path))
        if profile.id in profiles:
            raise EndpointProfileValidationError(f"duplicate endpoint profile id: {profile.id}")
        if profile.dialect not in KNOWN_DIALECT_IDS:
            raise EndpointProfileValidationError(f"unknown dialect: {profile.dialect}")
        profiles[profile.id] = profile

    return profiles


def ensure_endpoint_supports_prompt(
    endpoint: EndpointProfile,
    prompt: PromptDefinition,
) -> None:
    for capability in prompt.required_capabilities:
        field_name = CAPABILITY_FIELD_MAP.get(capability)
        if field_name is None:
            continue
        if getattr(endpoint.capabilities, field_name) is not True:
            raise EndpointProfileValidationError(
                f"endpoint {endpoint.id} does not support required capability {capability}"
            )


def _read_yaml(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise EndpointProfileValidationError(f"expected mapping payload in {path}")
    return data
