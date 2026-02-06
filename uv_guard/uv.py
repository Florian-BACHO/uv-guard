import os
import subprocess
from collections.abc import Sequence

import typer

from uv_guard.token import resolve_guardrails_token
from uv_guard.logs import error_console


def _resolve_index_flags() -> Sequence[str]:
    """Resolve the index flags to pass to uv."""
    guardrails_token = resolve_guardrails_token()

    return [
        f"--index=https://__token__:{guardrails_token}@pypi.guardrailsai.com/simple",
        "--default-index=https://pypi.org/simple",
    ]


def _call_uv(command: str, *args: str) -> None:
    """Call uv with the given command and arguments/options."""
    full_command = ["uv", command, "--quiet", *args]

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["LANG"] = "C.UTF-8"

    try:
        subprocess.run(full_command, check=True, stdout=subprocess.DEVNULL, env=env)
    except FileNotFoundError:
        error_console.print(
            "Error: Unable to invoke uv. Please ensure that uv is installed correctly and available in your system PATH."
        )
        raise typer.Exit(code=1)
    except subprocess.CalledProcessError as e:
        error_console.print(f"Error: uv command exited with code {e.returncode}")
        raise typer.Exit(code=1)


def init(*args) -> None:
    """Call the init command of uv."""
    _call_uv("init", *args)


def add(packages: Sequence[str], *args: str) -> None:
    """Call the add command of uv."""
    index_flags = _resolve_index_flags()

    _call_uv("add", *packages, *index_flags, *args)


def remove(packages: Sequence[str], *args: str) -> None:
    """Call the remove command of uv."""
    _call_uv("remove", *packages, *args)


def run(*args) -> None:
    """Call the run command of uv."""
    _call_uv("run", *args)


def sync(*args) -> None:
    """Call the sync command of uv."""
    index_flags = _resolve_index_flags()

    _call_uv("sync", *index_flags, *args)
