from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from modelfingerprint.contracts._common import ProbeCapabilityStatus, RuntimeExecutionClass
from modelfingerprint.contracts.run import CapabilityProbeResult, RuntimePolicySnapshot

RUNTIME_POLICY_ID = "single_request_progress_runtime_v1"
LIVE_CONTENT_OUTPUT_TOKEN_CAP = 3000
THINKING_NO_DATA_CHECKPOINTS_SECONDS = [10]
NON_THINKING_NO_DATA_CHECKPOINTS_SECONDS = [10]
PROGRESS_POLL_INTERVAL_SECONDS = 10
TOTAL_REQUEST_DEADLINE_SECONDS = 120
LEGACY_THINKING_ROUND_WINDOWS_SECONDS = [10]
LEGACY_NON_THINKING_ROUND_WINDOWS_SECONDS = [10]
LEGACY_MAX_PROMPT_ROUNDS = 1


def resolve_runtime_policy(
    *,
    capability_probe_payload: CapabilityProbeResult | Mapping[str, object] | None,
    supports_output_token_cap: bool,
) -> RuntimePolicySnapshot:
    thinking_status = _thinking_probe_status(capability_probe_payload)
    execution_class: RuntimeExecutionClass = (
        "thinking" if thinking_status == "supported" else "non_thinking"
    )
    no_data_checkpoints_seconds = (
        THINKING_NO_DATA_CHECKPOINTS_SECONDS
        if execution_class == "thinking"
        else NON_THINKING_NO_DATA_CHECKPOINTS_SECONDS
    )
    legacy_round_windows_seconds = (
        LEGACY_THINKING_ROUND_WINDOWS_SECONDS
        if execution_class == "thinking"
        else LEGACY_NON_THINKING_ROUND_WINDOWS_SECONDS
    )
    return RuntimePolicySnapshot(
        policy_id=RUNTIME_POLICY_ID,
        thinking_probe_status=thinking_status,
        execution_class=execution_class,
        no_data_checkpoints_seconds=list(no_data_checkpoints_seconds),
        progress_poll_interval_seconds=PROGRESS_POLL_INTERVAL_SECONDS,
        total_deadline_seconds=TOTAL_REQUEST_DEADLINE_SECONDS,
        output_token_cap=LIVE_CONTENT_OUTPUT_TOKEN_CAP if supports_output_token_cap else None,
        round_windows_seconds=list(legacy_round_windows_seconds),
        max_rounds=LEGACY_MAX_PROMPT_ROUNDS,
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
