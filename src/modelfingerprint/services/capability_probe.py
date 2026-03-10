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
    image = probe_image(base_url=base_url, api_key=api_key, model=model)
    outcomes = [thinking, tools, streaming, image]
    coverage_ratio = sum(
        outcome.status != "insufficient_evidence" for outcome in outcomes
    ) / len(outcomes)
    return {
        "base_url": base_url,
        "model": model,
        "probe_mode": "minimal",
        "probe_version": "v1",
        "coverage_ratio": coverage_ratio,
        "results": {
            "tools": asdict(tools),
            "thinking": asdict(thinking),
            "streaming": asdict(streaming),
            "image": asdict(image),
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
    response, failure = _post_json(
        url=_chat_completions_url(base_url),
        headers=_default_headers(base_url, api_key),
        body={
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
        },
    )
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


def probe_image(*, base_url: str, api_key: str, model: str) -> CapabilityProbeOutcome:
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
        return _with_capability(failure, "image")
    assert response is not None
    payload = _json_payload(response)
    outcome = classify_image_outcome(payload)
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


def classify_image_outcome(payload: dict[str, object]) -> CapabilityProbeOutcome:
    data = payload.get("data")
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            for key in ("url", "b64_json"):
                value = first.get(key)
                if isinstance(value, str) and value != "":
                    return CapabilityProbeOutcome(
                        capability="image",
                        status="supported",
                        detail=f"response returned image asset in {key}",
                        evidence={"asset_field": key},
                    )
    return CapabilityProbeOutcome(
        capability="image",
        status="accepted_but_ignored",
        detail="request succeeded but no image asset field was returned",
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
    except (urllib.error.URLError, TimeoutError) as exc:
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
