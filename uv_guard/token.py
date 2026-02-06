import typer
from guardrails.settings import settings
from uv_guard.logs import error_console


def resolve_guardrails_token() -> str:
    """Resolve the Guardrails-AI Hub token."""
    if settings.rc.token is None:
        error_console.print(
            "Error: Unable to find Guardrails-AI Token. Please run 'guardrails configure' first."
        )
        raise typer.Exit(1)

    return settings.rc.token
