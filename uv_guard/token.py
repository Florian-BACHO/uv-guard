from guardrails.settings import settings

from uv_guard.exceptions import UvGuardException


def resolve_guardrails_token() -> str:
    """Resolve the Guardrails-AI Hub token."""
    if settings.rc.token is None or settings.rc.token == "":
        raise UvGuardException(
            "Unable to find Guardrails-AI Token. Please run 'uv-guard configure' first."
        )

    return settings.rc.token
