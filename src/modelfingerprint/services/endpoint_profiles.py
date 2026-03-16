from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

from modelfingerprint.contracts.endpoint import EndpointProfile, ProtocolFamily
from modelfingerprint.contracts.prompt import PromptDefinition
from pydantic import ValidationError

KNOWN_DIALECT_IDS = frozenset({"openai_chat_v1"})
KNOWN_PROTOCOL_FAMILIES = frozenset[ProtocolFamily](
    {"openai_compatible", "anthropic_messages", "gemini_generate_content"}
)
DEFAULT_AD_HOC_API_KEY_ENV_VAR = "MODEL_FINGERPRINT_API_KEY"
AD_HOC_ENDPOINT_PROFILE_PREFIX = "adhoc-openai-chat-v1"

CAPABILITY_FIELD_MAP = {
    "chat_completions": None,
    "json_object_response": "supports_json_object_response",
    "visible_reasoning": "exposes_reasoning_text",
}


class EndpointProfileValidationError(ValueError):
    """Raised when endpoint-profile files violate repository invariants."""


class EndpointProfileResolutionError(ValueError):
    """Raised when a live target cannot be mapped to a unique endpoint profile."""


def load_endpoint_profiles(directory: Path) -> dict[str, EndpointProfile]:
    profiles: dict[str, EndpointProfile] = {}

    for path in sorted(directory.rglob("*.yaml")):
        try:
            profile = EndpointProfile.model_validate(_read_yaml(path))
        except ValidationError as exc:
            raise EndpointProfileValidationError(str(exc)) from exc
        if profile.id in profiles:
            raise EndpointProfileValidationError(f"duplicate endpoint profile id: {profile.id}")
        if profile.dialect not in KNOWN_DIALECT_IDS:
            raise EndpointProfileValidationError(f"unknown dialect: {profile.dialect}")
        if profile.protocol_family not in KNOWN_PROTOCOL_FAMILIES:
            raise EndpointProfileValidationError(
                f"unknown protocol_family: {profile.protocol_family}"
            )
        profiles[profile.id] = profile

    return profiles


def build_ad_hoc_endpoint_profile(
    *,
    base_url: str,
    model: str,
    auth_env_var: str = DEFAULT_AD_HOC_API_KEY_ENV_VAR,
) -> EndpointProfile:
    normalized_base_url = base_url.rstrip("/")
    profile_hash = hashlib.sha256(f"{normalized_base_url}\0{model}".encode()).hexdigest()[:12]
    return EndpointProfile.model_validate(
        {
            "id": f"{AD_HOC_ENDPOINT_PROFILE_PREFIX}:{profile_hash}",
            "dialect": "openai_chat_v1",
            "protocol_family": "openai_compatible",
            "base_url": normalized_base_url,
            "model": model,
            "auth": {
                "kind": "bearer_env",
                "env_var": auth_env_var,
            },
            "capabilities": {
                "exposes_reasoning_text": False,
                "supports_json_object_response": True,
                "supports_temperature": True,
                "supports_top_p": True,
                "supports_output_token_cap": True,
            },
            "request_mapping": {
                "output_token_cap_field": "max_tokens",
                "json_response_shape": {"type": "json_object"},
            },
            "response_mapping": {
                "answer_text_path": "choices.0.message.content",
                "finish_reason_path": "choices.0.finish_reason",
                "usage_paths": {
                    "prompt_tokens": "usage.prompt_tokens",
                    "output_tokens": "usage.completion_tokens",
                    "total_tokens": "usage.total_tokens",
                    "reasoning_tokens": "usage.completion_tokens_details.reasoning_tokens",
                },
            },
            "timeout_policy": {
                "connect_seconds": 10,
                "read_seconds": 120,
            },
            "retry_policy": {
                "max_attempts": 1,
                "retryable_statuses": [],
            },
        }
    )


def find_endpoint_profile(
    profiles: dict[str, EndpointProfile],
    *,
    base_url: str,
    model: str,
) -> EndpointProfile | None:
    normalized_base_url = base_url.rstrip("/")
    matches = [
        profile
        for profile in profiles.values()
        if str(profile.base_url).rstrip("/") == normalized_base_url and profile.model == model
    ]
    if not matches:
        return None
    if len(matches) > 1:
        ids = ", ".join(sorted(profile.id for profile in matches))
        raise EndpointProfileResolutionError(
            f"multiple endpoint profiles match base_url={base_url!r} model={model!r}: {ids}"
        )
    return matches[0]


def resolve_endpoint_profile(
    profiles: dict[str, EndpointProfile],
    *,
    base_url: str,
    model: str,
) -> EndpointProfile:
    match = find_endpoint_profile(profiles, base_url=base_url, model=model)
    if match is None:
        raise EndpointProfileResolutionError(
            f"no endpoint profile matches base_url={base_url!r} model={model!r}"
        )
    return match


def resolve_or_build_endpoint_profile(
    profiles: dict[str, EndpointProfile],
    *,
    base_url: str,
    model: str,
    auth_env_var: str = DEFAULT_AD_HOC_API_KEY_ENV_VAR,
) -> EndpointProfile:
    match = find_endpoint_profile(profiles, base_url=base_url, model=model)
    if match is not None:
        return match
    return build_ad_hoc_endpoint_profile(
        base_url=base_url,
        model=model,
        auth_env_var=auth_env_var,
    )


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
