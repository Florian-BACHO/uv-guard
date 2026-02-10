import os
import subprocess

import uv_guard.uv as uv
from uv_guard.exceptions import UvGuardException


def configure(*args):
    """Configure Guardrails AI.

    This function directly calls the configure CLI because uv run might try to sync with Guardrails packages that are
    not reachable before configuring.
    """
    command = ["guardrails", "configure", *args]

    env = os.environ.copy()
    stdout = None

    try:
        subprocess.run(command, check=True, stdout=stdout, env=env)
    except FileNotFoundError:
        raise UvGuardException(
            "Error: Unable to invoke guardrails. Please ensure that guardrails is installed correctly by running `uv tool install guardrails`."
        )
    except subprocess.CalledProcessError as e:
        raise UvGuardException(f"Error: uv command exited with code {e.returncode}")


def install(
    hub_uri: str,
) -> None:
    """Install the given guardrail with the Guardrails-AI CLI."""
    uv.run("guardrails", "hub", "install", hub_uri)


def uninstall(
    hub_uri: str,
) -> None:
    """Uninstall the given guardrail with the Guardrails-AI CLI."""
    uv.run("guardrails", "hub", "uninstall", hub_uri)
