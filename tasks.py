#! /usr/bin/env python
import shlex
import subprocess
import sys

import click


@click.group()
def cli():
    """Dev tasks."""


@cli.command()
def format():
    """Format code using isort and black."""
    _run("isort .")
    _run("black .")


@cli.command()
def lint():
    """Run isort, black, flake8 and mypy checks."""
    _run("isort --check-only --diff .")
    _run("black --check --diff .")
    _run("flake8 .")
    _run("mypy .")


@cli.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("pytest_args", nargs=-1, type=click.UNPROCESSED)
def test(pytest_args):
    """Run tests."""
    _run(["coverage", "run", "-m", "pytest"] + list(pytest_args))
    _run("coverage html")
    _run("coverage report")


@cli.command()
@click.pass_context
def all(ctx):
    """Run format, lint and tests."""
    ctx.invoke(format)
    ctx.invoke(lint)
    ctx.invoke(test)


def _run(args, **kwargs):
    if isinstance(args, str):
        args = shlex.split(args)
    click.secho(shlex.join(args), fg="cyan")
    process = subprocess.run(args, **kwargs)
    if process.returncode != 0:
        sys.exit(process.returncode)
    return process


if __name__ == "__main__":
    cli()
