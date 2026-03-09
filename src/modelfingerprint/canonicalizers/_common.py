from __future__ import annotations

import json
import re
from collections.abc import Mapping

from modelfingerprint.canonicalizers.base import CanonicalizationError
from modelfingerprint.contracts.run import CanonicalizationEvent


def parse_json_object(
    raw_output: str,
) -> tuple[dict[str, object], list[CanonicalizationEvent]]:
    candidate, events = strip_markdown_fence(raw_output)
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise CanonicalizationError(
            code="invalid_json",
            message="response body is not valid JSON",
        ) from exc
    if not isinstance(payload, Mapping):
        raise CanonicalizationError(
            code="invalid_json_shape",
            message="response body must be a JSON object",
        )
    return dict(payload), events


def strip_markdown_fence(raw_output: str) -> tuple[str, list[CanonicalizationEvent]]:
    stripped = raw_output.strip()
    match = re.fullmatch(r"```[a-zA-Z0-9_-]*\n?(.*?)```", stripped, flags=re.DOTALL)
    if match is None:
        return stripped, []
    return (
        match.group(1).strip(),
        [CanonicalizationEvent(code="removed_fence", message="removed markdown fence")],
    )


def normalize_key(value: str) -> tuple[str, bool]:
    normalized = value.strip().lower().replace(" ", "_")
    return normalized, normalized != value
