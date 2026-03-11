from __future__ import annotations

from collections.abc import Mapping

from modelfingerprint.extractors._shared_helpers import object_mapping, string_list


def shared_task_result(payload: Mapping[str, object]) -> dict[str, object]:
    return object_mapping(payload.get("task_result", {}), field_name="task_result")


def shared_evidence(payload: Mapping[str, object]) -> dict[str, object]:
    return object_mapping(payload.get("evidence", {}), field_name="evidence")


def shared_unknowns(payload: Mapping[str, object]) -> dict[str, object]:
    value = payload.get("unknowns", {})
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    if value in (None, False):
        return {}
    return {item: True for item in string_list(value, field_name="unknowns")}


def shared_violations(payload: Mapping[str, object]) -> list[str]:
    value = payload.get("violations", [])
    if isinstance(value, Mapping):
        if len(value) == 0:
            return []
        return [_format_violation_entry(key, item) for key, item in value.items()]
    return string_list(value, field_name="violations")


def _format_violation_entry(key: object, value: object) -> str:
    key_text = str(key)
    if value in (None, "", False):
        return key_text
    return f"{key_text}:{value}"
