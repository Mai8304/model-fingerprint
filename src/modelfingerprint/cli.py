from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import typer

from modelfingerprint import __version__
from modelfingerprint.adapters.openai_chat import ChatCompletionResult
from modelfingerprint.contracts.prompt import PromptDefinition
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.contracts.calibration import CalibrationArtifact
from modelfingerprint.services.calibrator import Calibrator
from modelfingerprint.services.comparator import compare_run
from modelfingerprint.services.profile_builder import build_profile
from modelfingerprint.services.prompt_bank import (
    PromptBankValidationError,
    load_candidate_prompts,
    load_suites,
    validate_suite_references,
    validate_suite_subset,
)
from modelfingerprint.services.suite_runner import SuiteRunner
from modelfingerprint.services.verdicts import decide_verdict
from modelfingerprint.settings import RepositoryPaths
from modelfingerprint.storage.filesystem import ensure_directories

app = typer.Typer(
    add_completion=False,
    help="CLI for file-based model fingerprint workflows.",
    no_args_is_help=True,
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
def validate_prompts(root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False)) -> None:
    try:
        prompts = load_candidate_prompts(root / "prompt-bank" / "candidates")
        suites = load_suites(root / "prompt-bank" / "suites")
        validate_suite_references(prompts, suites)
        validate_suite_subset(suites["default-v1"], suites["screening-v1"])
    except (KeyError, PromptBankValidationError, FileNotFoundError) as exc:
        raise typer.Exit(str(exc)) from exc

    typer.echo(f"validated {len(prompts)} candidate prompts and {len(suites)} suites")


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


@app.command("show-profile")
def show_profile(path: Path, json_output: bool = typer.Option(False, "--json")) -> None:
    artifact = ProfileArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))

    if json_output:
        typer.echo(json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True))
        return

    typer.echo(f"model_id: {artifact.model_id}")
    typer.echo(f"suite_id: {artifact.suite_id}")
    typer.echo(f"sample_count: {artifact.sample_count}")


@app.command("run-suite")
def run_suite(
    suite_id: str,
    target_label: str = typer.Option(..., "--target-label"),
    claimed_model: str | None = typer.Option(None, "--claimed-model"),
    root: Path = typer.Option(Path.cwd(), "--root", exists=True, file_okay=False),
    fixture_responses: Path = typer.Option(..., "--fixture-responses", exists=True, dir_okay=False),
    run_date: str = typer.Option("2026-03-09", "--run-date"),
) -> None:
    payload = json.loads(fixture_responses.read_text(encoding="utf-8"))

    class FixtureTransport:
        def complete(self, prompt: PromptDefinition) -> ChatCompletionResult:
            item = payload[prompt.id]
            return ChatCompletionResult(
                content=item["content"],
                input_tokens=item["input_tokens"],
                output_tokens=item["output_tokens"],
                total_tokens=item["total_tokens"],
            )

    runner = SuiteRunner(RepositoryPaths(root=root), transport=FixtureTransport())
    path = runner.run_suite(
        suite_id=suite_id,
        target_label=target_label,
        claimed_model=claimed_model,
        run_date=date.fromisoformat(run_date),
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
) -> None:
    run_artifact = _load_run(run)
    profiles = [_load_profile(path) for path in profile_paths]
    calibration_artifact = CalibrationArtifact.model_validate(
        json.loads(calibration.read_text(encoding="utf-8"))
    )
    comparison = compare_run(run_artifact, profiles)
    verdict = decide_verdict(comparison, calibration_artifact.thresholds)
    payload = {
        "top1_model": comparison.top1_model,
        "top1_similarity": comparison.top1_similarity,
        "top2_model": comparison.top2_model,
        "top2_similarity": comparison.top2_similarity,
        "margin": comparison.margin,
        "claimed_model": comparison.claimed_model,
        "claimed_model_similarity": comparison.claimed_model_similarity,
        "consistency": comparison.consistency,
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
    typer.echo(f"verdict: {payload['verdict']}")


def _load_run(path: Path) -> RunArtifact:
    return RunArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _load_profile(path: Path) -> ProfileArtifact:
    return ProfileArtifact.model_validate(json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    app()
