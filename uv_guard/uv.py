import os
import subprocess
from collections.abc import Sequence

from uv_guard.exceptions import UvGuardException
from uv_guard.token import resolve_guardrails_token


def _resolve_index_flags() -> Sequence[str]:
    """Resolve the index flags to pass to uv."""
    guardrails_token = resolve_guardrails_token()

    return [
        f"--index=https://__token__:{guardrails_token}@pypi.guardrailsai.com/simple",
        "--default-index=https://pypi.org/simple",
    ]


def call_uv(command: str, *args: str, quiet: bool = True) -> None:
    """Call uv with the given command and arguments/options."""
    full_command = ["uv", command]

    env = os.environ.copy()
    stdout = None

    if quiet:
        full_command.append("--quiet")
        env["PYTHONIOENCODING"] = "utf-8"
        env["LANG"] = "C.UTF-8"
        stdout = subprocess.DEVNULL

    full_command.extend(args)

    try:
        subprocess.run(full_command, check=True, stdout=stdout, env=env)
    except FileNotFoundError:
        raise UvGuardException(
            "Error: Unable to invoke uv. Please ensure that uv is installed correctly and available in your system PATH."
        )
    except subprocess.CalledProcessError as e:
        raise UvGuardException(f"Error: uv command exited with code {e.returncode}")


def init(*args) -> None:
    """Call the init command of uv."""
    call_uv("init", *args)


def add(packages: Sequence[str], *args: str, include_index_flags: bool = True) -> None:
    """Call the add command of uv."""
    index_flags = _resolve_index_flags() if include_index_flags else []

    call_uv("add", *packages, *index_flags, *args)


def remove(packages: Sequence[str], *args: str) -> None:
    """Call the remove command of uv."""
    call_uv("remove", *packages, *args)


def run(*args, quiet: bool = True) -> None:
    """Call the run command of uv."""
    call_uv("run", *args, quiet=quiet)


def sync(*args) -> None:
    """Call the sync command of uv."""
    index_flags = _resolve_index_flags()

    call_uv("sync", *index_flags, *args)
