from __future__ import annotations

import json
from pathlib import Path

import typer

from modelfingerprint import __version__
from modelfingerprint.contracts.profile import ProfileArtifact
from modelfingerprint.contracts.run import RunArtifact
from modelfingerprint.services.prompt_bank import (
    PromptBankValidationError,
    load_candidate_prompts,
    load_suites,
    validate_suite_references,
    validate_suite_subset,
)

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


if __name__ == "__main__":
    app()
