from __future__ import annotations

import typer

from modelfingerprint import __version__


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


if __name__ == "__main__":
    app()
