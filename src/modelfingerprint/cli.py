from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

import typer

from modelfingerprint import __version__
from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.contracts.endpoint import EndpointProfile
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.run import NormalizedCompletion, RunArtifact, UsageMetadata
from modelfingerprint.dialects.openai_chat import OpenAIChatDialectAdapter
from modelfingerprint.services.calibrator import Calibrator
from modelfingerprint.services.capability_probe import probe_capabilities
from modelfingerprint.services.comparator import compare_run
from modelfingerprint.services.comparison_artifact import build_comparison_artifact
from modelfingerprint.services.endpoint_profiles import (
    EndpointProfileValidationError,
    load_endpoint_profiles,
)
from modelfingerprint.services.feature_pipeline import PromptExecutionResult
from modelfingerprint.services.profile_builder import build_profile
from modelfingerprint.services.prompt_bank import (
    FINGERPRINT_SUITE_ID,
    QUICK_CHECK_SUITE_ID,
    PromptBankValidationError,
    load_candidate_prompts,
    load_suites,
    validate_release_suite_subsets,
    validate_suite_references,
    validate_suite_subset,
)
from modelfingerprint.services.runtime_policy import resolve_runtime_policy
from modelfingerprint.services.suite_runner import SuiteRunner
from modelfingerprint.services.verdicts import decide_verdict
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.storage.filesystem import ensure_directories
from modelfingerprint.transports.live_runner import LiveRunner

app = typer.Typer(
    add_completion=False,
    help="CLI for file-based model fingerprint workflows.",
    no_args_is_help=True,
)


@app.command("probe-capabilities")
def probe_capabilities_command(
    base_url: str = typer.Option(..., "--base-url"),
    api_key: str = typer.Option(..., "--api-key"),
    model: str = typer.Option(..., "--model"),
) -> None:
    typer.echo(
        json.dumps(
            probe_capabilities(base_url=base_url, api_key=api_key, model=model),
            indent=2,
            sort_keys=True,
        )
    )


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        help="Print the CLI version and exit.",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command("validate-prompts")
def validate_prompts(
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
) -> None:
    try:
        prompts = load_candidate_prompts(root / "prompt-bank" / "candidates")
        suites = load_suites(root / "prompt-bank" / "suites")
        validate_suite_references(prompts, suites)
        validate_suite_subset(suites[FINGERPRINT_SUITE_ID], suites[QUICK_CHECK_SUITE_ID])
        validate_release_suite_subsets(suites)
    except (KeyError, PromptBankValidationError, FileNotFoundError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"validated {len(prompts)} prompt definitions and {len(suites)} suites")


@app.command("validate-endpoints")
def validate_endpoints(
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
) -> None:
    try:
        profiles = load_endpoint_profiles(root / "endpoint-profiles")
    except (EndpointProfileValidationError, FileNotFoundError, ValueError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"validated {len(profiles)} endpoint profiles")


@app.command("show-suite")
def show_suite(
    suite_id: str,
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    suites = load_suites(root / "prompt-bank" / "suites")
    suite = suites.get(suite_id)
    if suite is None:
        raise typer.BadParameter(f"unknown suite id: {suite_id}")

    if json_output:
        typer.echo(json.dumps(suite.model_dump(mode="json"), indent=2, sort_keys=True))
        return

    typer.echo(f"id: {suite.id}")
    typer.echo(f"name: {suite.name}")
    typer.echo(f"prompt_ids: {', '.join(suite.prompt_ids)}")


@app.command("show-run")
def show_run(path: Path, json_output: bool = typer.Option(False, "--json")) -> None:
    artifact = RunArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))

    if json_output:
        typer.echo(json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True))
        return

    typer.echo(f"run_id: {artifact.run_id}")
    typer.echo(f"suite_id: {artifact.suite_id}")
    typer.echo(f"prompt_count: {len(artifact.prompts)}")
    if artifact.endpoint_profile_id is not None:
        typer.echo(f"endpoint_profile_id: {artifact.endpoint_profile_id}")
    typer.echo(f"answer_coverage_ratio: {_format_ratio(artifact.answer_coverage_ratio)}")
    typer.echo(f"reasoning_coverage_ratio: {_format_ratio(artifact.reasoning_coverage_ratio)}")
    typer.echo(f"capability_coverage_ratio: {_format_ratio(_run_capability_coverage(artifact))}")
    if artifact.runtime_policy is not None:
        typer.echo(f"runtime_execution_class: {artifact.runtime_policy.execution_class}")
        typer.echo(
            "runtime_no_data_checkpoints: "
            + ",".join(str(value) for value in artifact.runtime_policy.no_data_checkpoints_seconds)
        )
        typer.echo(
            "runtime_progress_poll_interval_seconds: "
            f"{artifact.runtime_policy.progress_poll_interval_seconds}"
        )
        typer.echo(
            f"runtime_total_deadline_seconds: {artifact.runtime_policy.total_deadline_seconds}"
        )
        typer.echo(
            f"runtime_output_token_cap: {artifact.runtime_policy.output_token_cap or 'n/a'}"
        )
    typer.echo(f"protocol_status: {_run_protocol_status(artifact)}")


@app.command("show-profile")
def show_profile(path: Path, json_output: bool = typer.Option(False, "--json")) -> None:
    artifact = ProfileArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))

    if json_output:
        typer.echo(json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True))
        return

    typer.echo(f"model_id: {artifact.model_id}")
    typer.echo(f"suite_id: {artifact.suite_id}")
    typer.echo(f"sample_count: {artifact.sample_count}")
    typer.echo(f"answer_coverage_ratio: {_format_ratio(artifact.answer_coverage_ratio)}")
    typer.echo(f"reasoning_coverage_ratio: {_format_ratio(artifact.reasoning_coverage_ratio)}")
    typer.echo(
        f"capability_coverage_ratio: {_format_ratio(_profile_capability_coverage(artifact))}"
    )
    typer.echo(
        "prompt_weights: "
        + ", ".join(f"{prompt.prompt_id}={prompt.weight:.4f}" for prompt in artifact.prompts)
    )


@app.command("run-suite")
def run_suite(
    suite_id: str,
    target_label: str = typer.Option(..., "--target-label"),
    claimed_model: str | None = typer.Option(None, "--claimed-model"),
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
    fixture_responses: Path | None = typer.Option(
        None,
        "--fixture-responses",
        exists=True,
        dir_okay=False,
    ),
    endpoint_profile: str | None = typer.Option(None, "--endpoint-profile"),
    run_date: str = typer.Option("2026-03-09", "--run-date"),
) -> None:
    if (fixture_responses is None) == (endpoint_profile is None):
        raise typer.BadParameter("provide exactly one of --fixture-responses or --endpoint-profile")

    paths = RepositoryPaths(root=root)
    transport: object
    capability_probe_payload: dict[str, object] | None = None
    if fixture_responses is not None:
        payload = json.loads(fixture_responses.read_text(encoding="utf-8"))

        class FixtureTransport:
            def execute(self, prompt: PromptDefinition) -> PromptExecutionResult:
                item = payload[prompt.id]
                reasoning_text = item.get("reasoning_content")
                completion = NormalizedCompletion(
                    answer_text=item["content"],
                    reasoning_text=reasoning_text,
                    reasoning_visible=isinstance(reasoning_text, str) and reasoning_text != "",
                    finish_reason=item.get("finish_reason"),
                    usage=UsageMetadata(
                        input_tokens=item["input_tokens"],
                        output_tokens=item["output_tokens"],
                        reasoning_tokens=item.get("reasoning_tokens", 0),
                        total_tokens=item["total_tokens"],
                    ),
                )
                return PromptExecutionResult(
                    prompt=prompt,
                    raw_output=item["content"],
                    usage=completion.usage,
                    completion=completion,
                )

        transport = FixtureTransport()
    else:
        profiles = load_endpoint_profiles(paths.endpoint_profiles_dir)
        endpoint = profiles.get(endpoint_profile or "")
        if endpoint is None:
            raise typer.BadParameter(f"unknown endpoint profile id: {endpoint_profile}")
        api_key = _load_endpoint_api_key(endpoint)
        capability_probe_payload = probe_capabilities(
            base_url=str(endpoint.base_url),
            api_key=api_key,
            model=endpoint.model,
        )
        runtime_policy = resolve_runtime_policy(
            capability_probe_payload=capability_probe_payload,
            supports_output_token_cap=endpoint.capabilities.supports_output_token_cap,
        )
        trace_dir = paths.traces_dir / run_date / f"{target_label}.{suite_id}"
        transport = LiveRunner(
            endpoint=endpoint,
            api_key=api_key,
            dialect=_build_dialect(endpoint),
            trace_dir=trace_dir,
            runtime_policy=runtime_policy,
        )

    runner = SuiteRunner(paths, transport=transport)
    path = runner.run_suite(
        suite_id=suite_id,
        target_label=target_label,
        claimed_model=claimed_model,
        run_date=date.fromisoformat(run_date),
        capability_probe_payload=capability_probe_payload,
    )
    typer.echo(path)


@app.command("build-profile")
def build_profile_command(
    model_id: str = typer.Option(..., "--model-id"),
    run_paths: list[Path] = typer.Option(..., "--run", exists=True, dir_okay=False),
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
) -> None:
    runs = [_load_run(path) for path in run_paths]
    prompts = load_candidate_prompts(root / "prompt-bank" / "candidates")
    weights = {prompt_id: prompt.weight_hint for prompt_id, prompt in prompts.items()}
    artifact = build_profile(model_id=model_id, runs=runs, prompt_weights=weights)
    output_dir = root / "profiles" / artifact.suite_id
    ensure_directories(output_dir)
    output_path = output_dir / f"{artifact.model_id}.json"
    output_path.write_text(
        json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    typer.echo(output_path)


@app.command("calibrate")
def calibrate_command(
    profile_paths: list[Path] = typer.Option(..., "--profile", exists=True, dir_okay=False),
    run_paths: list[Path] = typer.Option(..., "--run", exists=True, dir_okay=False),
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
) -> None:
    profiles = [_load_profile(path) for path in profile_paths]
    runs = [_load_run(path) for path in run_paths]
    calibrator = Calibrator(RepositoryPaths(root=root))
    path = calibrator.write(calibrator.calibrate(runs=runs, profiles=profiles))
    typer.echo(path)


@app.command("compare")
def compare_command(
    run: Path = typer.Option(..., "--run", exists=True, dir_okay=False),
    profile_paths: list[Path] = typer.Option(..., "--profile", exists=True, dir_okay=False),
    calibration: Path = typer.Option(..., "--calibration", exists=True, dir_okay=False),
    json_output: bool = typer.Option(False, "--json"),
    artifact_json: bool = typer.Option(False, "--artifact-json"),
) -> None:
    if json_output and artifact_json:
        raise typer.BadParameter("choose only one of --json or --artifact-json")

    run_artifact = _load_run(run)
    profiles = [_load_profile(path) for path in profile_paths]
    calibration_artifact = CalibrationArtifact.model_validate(
        json.loads(calibration.read_text(encoding="utf-8"))
    )
    if artifact_json:
        artifact = build_comparison_artifact(
            run=run_artifact,
            profiles=profiles,
            calibration=calibration_artifact,
        )
        typer.echo(json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True))
        return

    comparison = compare_run(run_artifact, profiles)
    verdict = decide_verdict(comparison, calibration_artifact)
    payload = {
        "top1_model": comparison.top1_model,
        "top1_similarity": comparison.top1_similarity,
        "top2_model": comparison.top2_model,
        "top2_similarity": comparison.top2_similarity,
        "margin": comparison.margin,
        "claimed_model": comparison.claimed_model,
        "claimed_model_similarity": comparison.claimed_model_similarity,
        "consistency": comparison.consistency,
        "content_similarity": comparison.content_similarity,
        "capability_similarity": comparison.capability_similarity,
        "answer_similarity": comparison.answer_similarity,
        "reasoning_similarity": comparison.reasoning_similarity,
        "transport_similarity": comparison.transport_similarity,
        "surface_similarity": comparison.surface_similarity,
        "answer_coverage_ratio": comparison.answer_coverage_ratio,
        "reasoning_coverage_ratio": comparison.reasoning_coverage_ratio,
        "capability_coverage_ratio": comparison.capability_coverage_ratio,
        "protocol_status": comparison.protocol_status,
        "protocol_issues": list(comparison.protocol_issues),
        "hard_mismatches": list(comparison.hard_mismatches),
        "verdict": verdict,
    }

    if json_output:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo(f"top1_model: {payload['top1_model']}")
    typer.echo(f"top1_similarity: {payload['top1_similarity']:.4f}")
    typer.echo(f"top2_model: {payload['top2_model']}")
    typer.echo(f"top2_similarity: {payload['top2_similarity']:.4f}")
    typer.echo(f"margin: {payload['margin']:.4f}")
    typer.echo(f"claimed_model_similarity: {payload['claimed_model_similarity']:.4f}")
    typer.echo(f"consistency: {payload['consistency']:.4f}")
    typer.echo(f"content_similarity: {_format_ratio(comparison.content_similarity)}")
    typer.echo(f"capability_similarity: {_format_ratio(comparison.capability_similarity)}")
    typer.echo(f"answer_similarity: {_format_ratio(comparison.answer_similarity)}")
    typer.echo(f"reasoning_similarity: {_format_ratio(comparison.reasoning_similarity)}")
    typer.echo(f"transport_similarity: {_format_ratio(comparison.transport_similarity)}")
    typer.echo(f"surface_similarity: {_format_ratio(comparison.surface_similarity)}")
    typer.echo(f"answer_coverage_ratio: {_format_ratio(comparison.answer_coverage_ratio)}")
    typer.echo(
        f"reasoning_coverage_ratio: {_format_ratio(comparison.reasoning_coverage_ratio)}"
    )
    typer.echo(
        f"capability_coverage_ratio: {_format_ratio(comparison.capability_coverage_ratio)}"
    )
    typer.echo(f"hard_mismatches: {', '.join(comparison.hard_mismatches) or 'none'}")
    typer.echo(f"protocol_status: {comparison.protocol_status}")
    typer.echo(f"verdict: {payload['verdict']}")


def _load_run(path: Path) -> RunArtifact:
    return RunArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _load_profile(path: Path) -> ProfileArtifact:
    return ProfileArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _format_ratio(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.4f}"


def _run_protocol_status(artifact: RunArtifact) -> str:
    if artifact.protocol_compatibility is None:
        return "unknown"
    if artifact.protocol_compatibility.satisfied:
        return "compatible"
    return "incompatible_protocol"


def _run_capability_coverage(artifact: RunArtifact) -> float | None:
    if artifact.capability_probe is None:
        return None
    return artifact.capability_probe.coverage_ratio


def _profile_capability_coverage(artifact: ProfileArtifact) -> float | None:
    if artifact.capability_profile is None:
        return None
    return artifact.capability_profile.coverage_ratio


def _build_dialect(endpoint: EndpointProfile) -> OpenAIChatDialectAdapter:
    if endpoint.dialect == "openai_chat_v1":
        return OpenAIChatDialectAdapter()
    raise typer.BadParameter(f"unsupported dialect: {endpoint.dialect}")


def _load_endpoint_api_key(endpoint: EndpointProfile) -> str:
    api_key = os.getenv(endpoint.auth.env_var)
    if not api_key:
        raise typer.BadParameter(
            f"missing API key in environment variable {endpoint.auth.env_var}"
        )
    return api_key


if __name__ == "__main__":
    app()
