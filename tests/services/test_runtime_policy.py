from __future__ import annotations

from modelfingerprint.services.runtime_policy import (
    LIVE_CONTENT_OUTPUT_TOKEN_CAP,
    MAX_PROMPT_ROUNDS,
    NON_THINKING_ROUND_WINDOWS_SECONDS,
    THINKING_ROUND_WINDOWS_SECONDS,
    resolve_runtime_policy,
)


def test_resolve_runtime_policy_uses_thinking_schedule_only_for_supported_probe() -> None:
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
    assert supported.round_windows_seconds == THINKING_ROUND_WINDOWS_SECONDS
    assert supported.max_rounds == MAX_PROMPT_ROUNDS
    assert supported.output_token_cap == LIVE_CONTENT_OUTPUT_TOKEN_CAP

    assert accepted_but_ignored.execution_class == "non_thinking"
    assert accepted_but_ignored.round_windows_seconds == NON_THINKING_ROUND_WINDOWS_SECONDS
    assert accepted_but_ignored.output_token_cap == LIVE_CONTENT_OUTPUT_TOKEN_CAP

    assert insufficient_evidence.execution_class == "non_thinking"
    assert insufficient_evidence.round_windows_seconds == NON_THINKING_ROUND_WINDOWS_SECONDS


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
    assert resolved.output_token_cap is None

