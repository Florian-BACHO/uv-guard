import uv_guard.uv as uv


def install_guardrail(
    hub_uri: str,
) -> None:
    """Install the given guardrail with the Guardrail-AI CLI."""
    uv.run("guardrails", "hub", "install", hub_uri)


def uninstall_guardrail(
    hub_uri: str,
) -> None:
    """Uninstall the given guardrail with the Guardrail-AI CLI."""
    uv.run("guardrails", "hub", "uninstall", hub_uri)
