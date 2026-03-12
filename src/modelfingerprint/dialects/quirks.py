from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass

from modelfingerprint.contracts.endpoint import EndpointProfile

MOONSHOT_KIMI_K25_QUIRKS = (
    "omit_temperature",
    "omit_top_p",
    "tools_require_thinking_disabled",
    "vision_prefer_data_url",
)

RED_SQUARE_REMOTE_URL = "https://dummyimage.com/64x64/ff0000/ff0000.png"
RED_SQUARE_DATA_URL = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAS0lEQVR42u3PQQkAAAgAsetfWiP4FgYrsKZeS0BAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEDgsqnc8OJg6Ln3AAAAAElFTkSuQmCC"
)


@dataclass(frozen=True)
class ProbeRetryPlan:
    body: dict[str, object]
    probe_path: str


@dataclass(frozen=True)
class VisionProbeAttempt:
    image_url: str
    max_tokens: int
    probe_path: str


def apply_request_quirks(
    body: Mapping[str, object],
    *,
    endpoint: EndpointProfile,
) -> dict[str, object]:
    mutated = dict(body)
    for quirk in endpoint.quirks:
        if quirk == "omit_temperature":
            mutated.pop("temperature", None)
        elif quirk == "omit_top_p":
            mutated.pop("top_p", None)
    return mutated


def resolve_probe_quirks(*, base_url: str, model: str) -> tuple[str, ...]:
    normalized_base_url = base_url.rstrip("/").lower()
    normalized_model = model.strip().lower()
    quirk_ids: list[str] = []
    if "api.moonshot.ai" in normalized_base_url and normalized_model == "kimi-k2.5":
        quirk_ids.extend(MOONSHOT_KIMI_K25_QUIRKS)
    return tuple(dict.fromkeys(quirk_ids))


def build_tools_probe_retry(
    *,
    request_body: Mapping[str, object],
    failure_status: str,
    failure_detail: str | None,
    quirk_ids: Collection[str],
) -> ProbeRetryPlan | None:
    if "tools_require_thinking_disabled" not in quirk_ids:
        return None
    if failure_status != "unsupported":
        return None
    normalized_detail = (failure_detail or "").lower()
    if "tool_choice" not in normalized_detail or "thinking enabled" not in normalized_detail:
        return None
    return ProbeRetryPlan(
        body={
            **request_body,
            "thinking": {"type": "disabled"},
        },
        probe_path="thinking_disabled_retry",
    )


def vision_probe_attempts(*, quirk_ids: Collection[str]) -> tuple[VisionProbeAttempt, ...]:
    attempts = [
        VisionProbeAttempt(
            image_url=RED_SQUARE_REMOTE_URL,
            max_tokens=64,
            probe_path="remote_image_primary",
        )
    ]
    if "vision_prefer_data_url" in quirk_ids:
        attempts.append(
            VisionProbeAttempt(
                image_url=RED_SQUARE_DATA_URL,
                max_tokens=256,
                probe_path="data_url_retry",
            )
        )
    return tuple(attempts)
