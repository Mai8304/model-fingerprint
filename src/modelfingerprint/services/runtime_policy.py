from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from modelfingerprint.contracts._common import ProbeCapabilityStatus, RuntimeExecutionClass
from modelfingerprint.contracts.run import CapabilityProbeResult, RuntimePolicySnapshot

RUNTIME_POLICY_ID = "thinking_aware_runtime_v1"
LIVE_CONTENT_OUTPUT_TOKEN_CAP = 3000
THINKING_ROUND_WINDOWS_SECONDS = [30, 30]
NON_THINKING_ROUND_WINDOWS_SECONDS = [30]
MAX_PROMPT_ROUNDS = 2


def resolve_runtime_policy(
    *,
    capability_probe_payload: CapabilityProbeResult | Mapping[str, object] | None,
    supports_output_token_cap: bool,
) -> RuntimePolicySnapshot:
    thinking_status = _thinking_probe_status(capability_probe_payload)
    execution_class: RuntimeExecutionClass = (
        "thinking" if thinking_status == "supported" else "non_thinking"
    )
    round_windows_seconds = (
        THINKING_ROUND_WINDOWS_SECONDS
        if execution_class == "thinking"
        else NON_THINKING_ROUND_WINDOWS_SECONDS
    )
    return RuntimePolicySnapshot(
        policy_id=RUNTIME_POLICY_ID,
        thinking_probe_status=thinking_status,
        execution_class=execution_class,
        round_windows_seconds=list(round_windows_seconds),
        max_rounds=MAX_PROMPT_ROUNDS,
        output_token_cap=LIVE_CONTENT_OUTPUT_TOKEN_CAP if supports_output_token_cap else None,
    )


def _thinking_probe_status(
    capability_probe_payload: CapabilityProbeResult | Mapping[str, object] | None,
) -> ProbeCapabilityStatus:
    if capability_probe_payload is None:
        return "insufficient_evidence"
    if isinstance(capability_probe_payload, CapabilityProbeResult):
        outcome = capability_probe_payload.capabilities.get("thinking")
        return (
            outcome.status
            if outcome is not None
            else "insufficient_evidence"
        )
    results = capability_probe_payload.get("results")
    if not isinstance(results, Mapping):
        return "insufficient_evidence"
    thinking = results.get("thinking")
    if not isinstance(thinking, Mapping):
        return "insufficient_evidence"
    status = thinking.get("status")
    if status in {
        "supported",
        "accepted_but_ignored",
        "unsupported",
        "insufficient_evidence",
    }:
        return cast(ProbeCapabilityStatus, status)
    return "insufficient_evidence"
