import uv_guard.uv as uv


def configure(*args):
    """Configure Guardrails AI."""
    uv.run("guardrails", "configure", *args, quiet=False)


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
