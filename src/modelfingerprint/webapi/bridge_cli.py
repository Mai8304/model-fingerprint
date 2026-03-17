from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.webapi.contracts import WebRunInput, WebRunResult
from modelfingerprint.webapi.fingerprint_chain import FingerprintChainError
from modelfingerprint.webapi.fingerprints import display_model_label, list_fingerprint_models
from modelfingerprint.webapi.run_orchestrator import RunOrchestrator, WebRunConfigurationError
from modelfingerprint.webapi.run_projection import project_run_snapshot
from modelfingerprint.webapi.run_store import RunStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modelfingerprint.webapi.bridge_cli")
    parser.add_argument("--root", required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-fingerprints")
    subparsers.add_parser("create-run")

    run_worker = subparsers.add_parser("run-worker")
    run_worker.add_argument("--run-id", required=True)

    get_run = subparsers.add_parser("get-run")
    get_run.add_argument("--run-id", required=True)

    get_result = subparsers.add_parser("get-result")
    get_result.add_argument("--run-id", required=True)

    cancel_run = subparsers.add_parser("cancel-run")
    cancel_run.add_argument("--run-id", required=True)

    args = parser.parse_args(argv)
    paths = RepositoryPaths(root=Path(args.root))
    store = RunStore(paths.root / ".webapi" / "runs")

    try:
        if args.command == "list-fingerprints":
            items = list_fingerprint_models(paths)
            return _emit_json({"items": [item.model_dump(mode="json") for item in items]})
        if args.command == "create-run":
            payload = _read_stdin_json()
            run_id, input_payload = _parse_create_run_payload(payload)
            orchestrator = RunOrchestrator(paths=paths, store=store)
            record = orchestrator.initialize_run(run_id=run_id, input=input_payload)
            return _emit_json(_record_brief(record))
        if args.command == "run-worker":
            api_key = os.environ.get("MODELFINGERPRINT_WEB_API_KEY")
            if not api_key:
                raise WebRunConfigurationError(
                    code="INVALID_REQUEST",
                    message="missing MODELFINGERPRINT_WEB_API_KEY for worker execution",
                )
            record = store.get(args.run_id)
            orchestrator = RunOrchestrator(paths=paths, store=store)
            orchestrator.run_with_api_key(
                run_id=args.run_id,
                input=record.input,
                api_key=api_key,
            )
            return 0
        if args.command == "get-run":
            record = store.get(args.run_id)
            snapshot = project_run_snapshot(record)
            return _emit_json(snapshot.model_dump(mode="json"))
        if args.command == "get-result":
            record = store.get(args.run_id)
            result = _project_run_result(record)
            if result is None:
                return _emit_error(
                    code="RUN_NOT_COMPLETED",
                    message="run is still in progress",
                    status=409,
                )
            return _emit_json(result.model_dump(mode="json"))
        if args.command == "cancel-run":
            record = store.mark_cancel_requested(args.run_id)
            return _emit_json(_record_brief(record))
    except FileNotFoundError:
        return _emit_error(
            code="RUN_NOT_FOUND",
            message="run_id does not exist",
            status=404,
        )
    except WebRunConfigurationError as exc:
        return _emit_error(
            code=exc.code,
            message=exc.message,
            status=404 if exc.code == "UNKNOWN_FINGERPRINT_MODEL" else 400,
        )
    except FingerprintChainError as exc:
        return _emit_error(
            code="FINGERPRINT_CHAIN_INVALID",
            message=str(exc),
            status=500,
        )
    except ValidationError as exc:
        return _emit_error(
            code="INVALID_REQUEST",
            message=str(exc),
            status=400,
        )

    return _emit_error(code="INVALID_REQUEST", message="unsupported bridge command", status=400)


def _project_run_result(record) -> WebRunResult | None:
    if record.result is not None:
        return record.result
    if record.result_state not in {"configuration_error", "stopped"}:
        return None

    return WebRunResult.model_validate(
        {
            "run_id": record.run_id,
            "result_state": record.result_state,
            "selected_fingerprint": {
                "id": record.input.fingerprint_model_id,
                "label": display_model_label(record.input.fingerprint_model_id),
            },
            "completed_prompts": sum(
                1 for prompt in record.prompts if prompt.status == "completed"
            ),
            "total_prompts": len(record.prompts),
            "verdict": None,
            "summary": None,
            "candidates": [],
            "diagnostics": {
                "protocol_status": "insufficient_evidence",
                "protocol_issues": [],
                "hard_mismatches": [],
            },
        }
    )


def _record_brief(record) -> dict[str, object]:
    return {
        "run_id": record.run_id,
        "run_status": record.run_status,
        "result_state": record.result_state,
        "cancel_requested": record.cancel_requested,
    }


def _read_stdin_json() -> dict[str, object]:
    raw = sys.stdin.read()
    if raw == "":
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise WebRunConfigurationError(
            code="INVALID_REQUEST",
            message="expected object payload",
        )
    return payload


def _parse_create_run_payload(payload: dict[str, object]) -> tuple[str, WebRunInput]:
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or run_id.strip() == "":
        raise WebRunConfigurationError(
            code="INVALID_REQUEST",
            message="run_id is required",
        )

    input_payload = WebRunInput.model_validate(
        {
            key: value
            for key, value in payload.items()
            if key != "run_id"
        }
    )
    return run_id, input_payload


def _emit_json(payload: dict[str, object]) -> int:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


def _emit_error(*, code: str, message: str, status: int) -> int:
    sys.stdout.write(
        json.dumps(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "status": status,
                }
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
