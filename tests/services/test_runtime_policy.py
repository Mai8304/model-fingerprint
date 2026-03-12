from __future__ import annotations

from modelfingerprint.services.runtime_policy import (
    LIVE_CONTENT_OUTPUT_TOKEN_CAP,
    NON_THINKING_NO_DATA_CHECKPOINTS_SECONDS,
    PROGRESS_POLL_INTERVAL_SECONDS,
    THINKING_NO_DATA_CHECKPOINTS_SECONDS,
    TOTAL_REQUEST_DEADLINE_SECONDS,
    resolve_runtime_policy,
)


def test_resolve_runtime_policy_uses_thinking_monitoring_schedule_only_for_supported_probe(
) -> None:
    assert THINKING_NO_DATA_CHECKPOINTS_SECONDS == [60, 90]
    assert NON_THINKING_NO_DATA_CHECKPOINTS_SECONDS == [60]

    supported = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "supported",
                }
            }
        },
        supports_output_token_cap=True,
    )
    accepted_but_ignored = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "accepted_but_ignored",
                }
            }
        },
        supports_output_token_cap=True,
    )
    insufficient_evidence = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "insufficient_evidence",
                }
            }
        },
        supports_output_token_cap=True,
    )

    assert supported.execution_class == "thinking"
    assert supported.no_data_checkpoints_seconds == THINKING_NO_DATA_CHECKPOINTS_SECONDS
    assert supported.progress_poll_interval_seconds == PROGRESS_POLL_INTERVAL_SECONDS
    assert supported.total_deadline_seconds == TOTAL_REQUEST_DEADLINE_SECONDS
    assert supported.output_token_cap == LIVE_CONTENT_OUTPUT_TOKEN_CAP

    assert accepted_but_ignored.execution_class == "non_thinking"
    assert (
        accepted_but_ignored.no_data_checkpoints_seconds
        == NON_THINKING_NO_DATA_CHECKPOINTS_SECONDS
    )
    assert accepted_but_ignored.output_token_cap == LIVE_CONTENT_OUTPUT_TOKEN_CAP

    assert insufficient_evidence.execution_class == "non_thinking"
    assert (
        insufficient_evidence.no_data_checkpoints_seconds
        == NON_THINKING_NO_DATA_CHECKPOINTS_SECONDS
    )


def test_resolve_runtime_policy_omits_output_cap_when_endpoint_does_not_support_it() -> None:
    resolved = resolve_runtime_policy(
        capability_probe_payload={
            "results": {
                "thinking": {
                    "status": "supported",
                }
            }
        },
        supports_output_token_cap=False,
    )

    assert resolved.execution_class == "thinking"
    assert resolved.no_data_checkpoints_seconds == THINKING_NO_DATA_CHECKPOINTS_SECONDS
    assert resolved.output_token_cap is None
