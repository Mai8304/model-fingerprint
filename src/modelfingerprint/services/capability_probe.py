from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

from modelfingerprint.http_defaults import DEFAULT_BROWSER_USER_AGENT

ProbeStatus = Literal[
    "supported",
    "accepted_but_ignored",
    "unsupported",
    "insufficient_evidence",
]


@dataclass(frozen=True)
class CapabilityProbeOutcome:
    capability: str
    status: ProbeStatus
    detail: str | None = None
    evidence: dict[str, object] = field(default_factory=dict)
    http_status: int | None = None
    latency_ms: int | None = None


@dataclass(frozen=True)
class HttpProbeResponse:
    status_code: int
    headers: dict[str, str]
    body: bytes
    latency_ms: int


def probe_capabilities(*, base_url: str, api_key: str, model: str) -> dict[str, object]:
    thinking = probe_thinking(base_url=base_url, api_key=api_key, model=model)
    tools = probe_tools(base_url=base_url, api_key=api_key, model=model)
    streaming = probe_streaming(base_url=base_url, api_key=api_key, model=model)
    image_generation = probe_image_generation(
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    vision_understanding = probe_vision_understanding(
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    outcomes = [thinking, tools, streaming, image_generation, vision_understanding]
    coverage_ratio = sum(
        outcome.status != "insufficient_evidence" for outcome in outcomes
    ) / len(outcomes)
    return {
        "base_url": base_url,
        "model": model,
        "probe_mode": "minimal",
        "probe_version": "v2",
        "coverage_ratio": coverage_ratio,
        "results": {
            "tools": asdict(tools),
            "thinking": asdict(thinking),
            "streaming": asdict(streaming),
            "image_generation": asdict(image_generation),
            "vision_understanding": asdict(vision_understanding),
        },
    }


def probe_thinking(*, base_url: str, api_key: str, model: str) -> CapabilityProbeOutcome:
    response, failure = _post_json(
        url=_chat_completions_url(base_url),
        headers=_default_headers(base_url, api_key),
        body={
            "model": model,
            "messages": [{"role": "user", "content": "只返回 ok"}],
            "max_tokens": 32,
        },
    )
    if failure is not None:
        return _with_capability(failure, "thinking")
    assert response is not None
    payload = _json_payload(response)
    outcome = classify_thinking_outcome(payload)
    return _with_transport(outcome, response)


def probe_tools(*, base_url: str, api_key: str, model: str) -> CapabilityProbeOutcome:
    request_body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "调用 ping 工具，不要输出自然语言。",
            }
        ],
        "max_tokens": 64,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "ping",
                    "description": "Return pong.",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            }
        ],
        "tool_choice": {
            "type": "function",
            "function": {"name": "ping"},
        },
    }
    response, failure = _post_json(
        url=_chat_completions_url(base_url),
        headers=_default_headers(base_url, api_key),
        body=request_body,
    )
    if failure is not None and _should_retry_tools_with_thinking_disabled(failure):
        retry_response, retry_failure = _post_json(
            url=_chat_completions_url(base_url),
            headers=_default_headers(base_url, api_key),
            body={
                **request_body,
                "thinking": {"type": "disabled"},
            },
        )
        if retry_failure is None:
            assert retry_response is not None
            payload = _json_payload(retry_response)
            outcome = classify_tools_outcome(payload)
            return _with_probe_path(_with_transport(outcome, retry_response), "thinking_disabled_retry")
        failure = retry_failure
    if failure is not None:
        return _with_capability(failure, "tools")
    assert response is not None
    payload = _json_payload(response)
    outcome = classify_tools_outcome(payload)
    return _with_transport(outcome, response)


def probe_streaming(*, base_url: str, api_key: str, model: str) -> CapabilityProbeOutcome:
    response, failure = _post_json(
        url=_chat_completions_url(base_url),
        headers=_default_headers(base_url, api_key, accept="text/event-stream"),
        body={
            "model": model,
            "messages": [{"role": "user", "content": "只返回 ok"}],
            "max_tokens": 16,
            "stream": True,
        },
    )
    if failure is not None:
        return _with_capability(failure, "streaming")
    assert response is not None
    outcome = classify_streaming_outcome(
        status_code=response.status_code,
        content_type=response.headers.get("content-type", ""),
        body=response.body,
    )
    return _with_transport(outcome, response)


def probe_image_generation(
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> CapabilityProbeOutcome:
    if _should_probe_image_generation_via_chat_completions(base_url=base_url):
        response, failure = _post_json(
            url=_chat_completions_url(base_url),
            headers=_default_headers(base_url, api_key),
            body={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Generate a 256x256 image of a red square.",
                            }
                        ],
                    }
                ],
                "modalities": ["image", "text"],
            },
        )
        if failure is not None:
            return _with_capability(failure, "image_generation")
        assert response is not None
        payload = _json_payload(response)
        outcome = classify_image_generation_outcome(payload)
        return _with_transport(outcome, response)

    response, failure = _post_json(
        url=_images_generations_url(base_url),
        headers=_default_headers(base_url, api_key),
        body={
            "model": model,
            "prompt": "a red square",
            "size": "256x256",
            "n": 1,
        },
    )
    if failure is not None:
        return _with_capability(failure, "image_generation")
    assert response is not None
    payload = _json_payload(response)
    outcome = classify_image_generation_outcome(payload)
    return _with_transport(outcome, response)


def probe_vision_understanding(
    *,
    base_url: str,
    api_key: str,
    model: str,
) -> CapabilityProbeOutcome:
    primary = _probe_vision_understanding_once(
        base_url=base_url,
        api_key=api_key,
        model=model,
        image_url=_red_square_remote_url(),
        max_tokens=64,
    )
    if primary.status == "supported":
        return _with_probe_path(primary, "remote_image_primary")
    if not _should_retry_vision_understanding(primary):
        return primary

    fallback = _probe_vision_understanding_once(
        base_url=base_url,
        api_key=api_key,
        model=model,
        image_url=_red_square_data_url(),
        max_tokens=256,
    )
    if fallback.status != "supported":
        return primary

    return _with_probe_path(fallback, "data_url_retry")


def _probe_vision_understanding_once(
    *,
    base_url: str,
    api_key: str,
    model: str,
    image_url: str,
    max_tokens: int,
) -> CapabilityProbeOutcome:
    response, failure = _post_json(
        url=_chat_completions_url(base_url),
        headers=_default_headers(base_url, api_key),
        body={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "图里是什么颜色的方块？只回答颜色。"},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            "max_tokens": max_tokens,
        },
    )
    if failure is not None:
        return _with_capability(failure, "vision_understanding")
    assert response is not None
    payload = _json_payload(response)
    outcome = classify_vision_understanding_outcome(payload)
    return _with_transport(outcome, response)


def classify_thinking_outcome(payload: dict[str, object]) -> CapabilityProbeOutcome:
    choice = _first_choice(payload)
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    if isinstance(message, dict):
        for key in ("reasoning", "reasoning_content", "thinking"):
            value = message.get(key)
            if isinstance(value, str) and value.strip():
                return CapabilityProbeOutcome(
                    capability="thinking",
                    status="supported",
                    detail=f"{key} field is populated",
                    evidence={"field": key},
                )

    reasoning_tokens = _reasoning_tokens(payload)
    if reasoning_tokens > 0:
        return CapabilityProbeOutcome(
            capability="thinking",
            status="supported",
            detail=f"reasoning_tokens={reasoning_tokens}",
            evidence={"reasoning_tokens": reasoning_tokens},
        )

    return CapabilityProbeOutcome(
        capability="thinking",
        status="accepted_but_ignored",
        detail="request succeeded but no visible reasoning signal was returned",
    )


def classify_tools_outcome(payload: dict[str, object]) -> CapabilityProbeOutcome:
    choice = _first_choice(payload)
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
    if isinstance(message, dict):
        tool_calls = message.get("tool_calls")
        if isinstance(tool_calls, list) and tool_calls:
            return CapabilityProbeOutcome(
                capability="tools",
                status="supported",
                detail="response contains tool_calls",
                evidence={"finish_reason": finish_reason, "tool_call_count": len(tool_calls)},
            )
    if finish_reason == "tool_calls":
        return CapabilityProbeOutcome(
            capability="tools",
            status="supported",
            detail="finish_reason=tool_calls",
            evidence={"finish_reason": finish_reason},
        )
    return CapabilityProbeOutcome(
        capability="tools",
        status="accepted_but_ignored",
        detail="request succeeded but no tool call was returned",
        evidence={"finish_reason": finish_reason} if finish_reason is not None else {},
    )


def classify_streaming_outcome(
    *,
    status_code: int,
    content_type: str,
    body: bytes,
) -> CapabilityProbeOutcome:
    if status_code >= 400:
        return CapabilityProbeOutcome(
            capability="streaming",
            status="unsupported",
            detail=f"stream request returned HTTP {status_code}",
            evidence={"content_type": content_type},
            http_status=status_code,
        )
    decoded = body.decode("utf-8", errors="replace")
    if "text/event-stream" in content_type.lower() or "data:" in decoded:
        return CapabilityProbeOutcome(
            capability="streaming",
            status="supported",
            detail="response used SSE event chunks",
            evidence={"content_type": content_type},
        )
    return CapabilityProbeOutcome(
        capability="streaming",
        status="accepted_but_ignored",
        detail="request succeeded but response was not streamed as SSE",
        evidence={"content_type": content_type},
    )


def classify_image_generation_outcome(payload: dict[str, object]) -> CapabilityProbeOutcome:
    choice = _first_choice(payload)
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    if isinstance(message, dict):
        images = message.get("images")
        if isinstance(images, list) and images and isinstance(images[0], dict):
            first_image = images[0]
            for key in ("image_url", "imageUrl"):
                nested = first_image.get(key)
                if isinstance(nested, dict):
                    value = nested.get("url")
                    if isinstance(value, str) and value != "":
                        return CapabilityProbeOutcome(
                            capability="image_generation",
                            status="supported",
                            detail=f"response returned image asset in choices.0.message.images.0.{key}.url",
                            evidence={"asset_field": f"choices.0.message.images.0.{key}.url"},
                        )

    data = payload.get("data")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            for key in ("url", "b64_json"):
                value = first.get(key)
                if isinstance(value, str) and value != "":
                    return CapabilityProbeOutcome(
                        capability="image_generation",
                        status="supported",
                        detail=f"response returned image asset in {key}",
                        evidence={"asset_field": key},
                    )
    return CapabilityProbeOutcome(
        capability="image_generation",
        status="accepted_but_ignored",
        detail="request succeeded but no image asset field was returned",
    )


def classify_vision_understanding_outcome(payload: dict[str, object]) -> CapabilityProbeOutcome:
    choice = _first_choice(payload)
    message = choice.get("message", {}) if isinstance(choice, dict) else {}
    answer_text = _message_text_content(message if isinstance(message, dict) else {})
    normalized_answer = _normalize_vision_answer(answer_text)
    if normalized_answer is not None:
        return CapabilityProbeOutcome(
            capability="vision_understanding",
            status="supported",
            detail=f"recognized grounded answer: {normalized_answer}",
            evidence={"normalized_answer": normalized_answer},
        )
    return CapabilityProbeOutcome(
        capability="vision_understanding",
        status="accepted_but_ignored",
        detail="request succeeded but no recognized grounded answer was returned",
    )


def _with_transport(
    outcome: CapabilityProbeOutcome,
    response: HttpProbeResponse,
) -> CapabilityProbeOutcome:
    evidence = dict(outcome.evidence)
    evidence.setdefault("http_status", response.status_code)
    return CapabilityProbeOutcome(
        capability=outcome.capability,
        status=outcome.status,
        detail=outcome.detail,
        evidence=evidence,
        http_status=response.status_code,
        latency_ms=response.latency_ms,
    )


def _with_capability(
    outcome: CapabilityProbeOutcome,
    capability: str,
) -> CapabilityProbeOutcome:
    return CapabilityProbeOutcome(
        capability=capability,
        status=outcome.status,
        detail=outcome.detail,
        evidence=outcome.evidence,
        http_status=outcome.http_status,
        latency_ms=outcome.latency_ms,
    )


def _with_probe_path(
    outcome: CapabilityProbeOutcome,
    probe_path: str,
) -> CapabilityProbeOutcome:
    evidence = dict(outcome.evidence)
    evidence["probe_path"] = probe_path
    return CapabilityProbeOutcome(
        capability=outcome.capability,
        status=outcome.status,
        detail=outcome.detail,
        evidence=evidence,
        http_status=outcome.http_status,
        latency_ms=outcome.latency_ms,
    )


def _post_json(
    *,
    url: str,
    headers: dict[str, str],
    body: dict[str, object],
    timeout_seconds: int = 90,
) -> tuple[HttpProbeResponse | None, CapabilityProbeOutcome | None]:
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = response.read()
            elapsed = int((time.time() - started) * 1000)
            return (
                HttpProbeResponse(
                    status_code=response.status,
                    headers=dict(response.headers.items()),
                    body=payload,
                    latency_ms=elapsed,
                ),
                None,
            )
    except urllib.error.HTTPError as exc:
        elapsed = int((time.time() - started) * 1000)
        body_text = exc.read().decode("utf-8", errors="replace")
        return None, _failure_outcome(
            status_code=exc.code,
            latency_ms=elapsed,
            detail=body_text,
        )
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        elapsed = int((time.time() - started) * 1000)
        return None, CapabilityProbeOutcome(
            capability="transport",
            status="insufficient_evidence",
            detail=str(exc),
            evidence={},
            latency_ms=elapsed,
        )


def _failure_outcome(
    *,
    status_code: int,
    latency_ms: int,
    detail: str,
) -> CapabilityProbeOutcome:
    if status_code in {400, 404, 405, 422}:
        status: ProbeStatus = "unsupported"
    else:
        status = "insufficient_evidence"
    return CapabilityProbeOutcome(
        capability="transport",
        status=status,
        detail=detail,
        evidence={"http_status": status_code},
        http_status=status_code,
        latency_ms=latency_ms,
    )


def _json_payload(response: HttpProbeResponse) -> dict[str, object]:
    return cast(dict[str, object], json.loads(response.body.decode("utf-8")))


def _default_headers(
    base_url: str,
    api_key: str,
    *,
    accept: str = "application/json",
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": accept,
        "User-Agent": DEFAULT_BROWSER_USER_AGENT,
    }
    if "openrouter.ai" in base_url:
        headers["HTTP-Referer"] = "https://codex.local"
        headers["X-Title"] = "Codex Model Fingerprint"
    return headers


def _chat_completions_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


def _images_generations_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/images/generations"


def _should_probe_image_generation_via_chat_completions(*, base_url: str) -> bool:
    return "openrouter.ai" in base_url


def _first_choice(payload: dict[str, object]) -> dict[str, object]:
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        return choices[0]
    return {}


def _reasoning_tokens(payload: dict[str, object]) -> int:
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return 0
    details = usage.get("completion_tokens_details")
    if not isinstance(details, dict):
        return 0
    value = details.get("reasoning_tokens")
    return value if isinstance(value, int) else 0


def _message_text_content(message: dict[str, object]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if not isinstance(item, dict):
                continue
            text_value = item.get("text")
            if isinstance(text_value, str):
                parts.append(text_value)
        return "".join(parts)
    return ""


def _normalize_vision_answer(answer_text: str) -> str | None:
    normalized = "".join(ch for ch in answer_text.strip().lower() if ch.isalnum())
    if normalized == "":
        return None
    if normalized in {"red", "红", "红色", "redsquare", "红色方块", "红方块"}:
        return "red"
    return None


def _should_retry_vision_understanding(outcome: CapabilityProbeOutcome) -> bool:
    if outcome.status == "accepted_but_ignored":
        return True
    return outcome.status == "unsupported" and outcome.http_status == 400


def _red_square_data_url() -> str:
    return (
        "data:image/png;base64,"
        "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAS0lEQVR42u3PQQkAAAgAsetfWiP4FgYrsKZeS0BAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEDgsqnc8OJg6Ln3AAAAAElFTkSuQmCC"
    )


def _red_square_remote_url() -> str:
    return "https://dummyimage.com/64x64/ff0000/ff0000.png"


def _should_retry_tools_with_thinking_disabled(outcome: CapabilityProbeOutcome) -> bool:
    if outcome.status != "unsupported":
        return False
    detail = (outcome.detail or "").lower()
    return "tool_choice" in detail and "thinking enabled" in detail
