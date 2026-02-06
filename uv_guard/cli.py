from typing import Annotated, List, cast, Iterable

import typer

from rich.progress import track

from uv_guard.package import resolve_python_package, is_guardrails_hub_uri
from uv_guard.guardrails import install_guardrail, uninstall_guardrail
from uv_guard.project import ProjectManager
from uv_guard.logs import console
import uv_guard.uv as uv

app = typer.Typer(
    name="uv-gard",
    help="UV-Guard is a command-line tool for managing uv projects that include Guardrails AI validators.",
)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def init(ctx: typer.Context) -> None:
    """
    Create a new project.

    Execute 'uv init --help' for more information about uv arguments and options.
    """
    with console.status("Initializing project...\n") as status:
        uv.init(*ctx.args)

        status.update("Initializing dependencies...\n")
        uv.add(["guardrails-ai"])

    console.print("[bold green]Project successfully initialized.[/bold green]")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def add(
    ctx: typer.Context,
    packages: Annotated[
        List[str],
        typer.Argument(
            help="The packages to add, as PEP 508 requirements or Guardrails Hub URIs."
        ),
    ],
) -> None:
    """
    Add dependencies to the project. Works for both Python and Guardrails Hub URIs.

    Execute 'uv add --help' for more information about uv arguments and options.
    """
    with console.status("Adding guardrails...\n") as status:
        with ProjectManager() as project:
            # Add the new guardrails to the project TOML
            # Update hub uris if versions are already specified in the project and are not overridden
            packages = [
                project.add_guardrail(pkg) if is_guardrails_hub_uri(pkg) else pkg
                for pkg in packages
            ]

        status.update("Adding Python dependencies...\n")
        # Resolve python package names (convert hub uris to python packages)
        python_packages = [resolve_python_package(pkg) for pkg in packages]
        # Add packages to uv
        uv.add(["guardrails-ai"] + python_packages, *ctx.args)

    guardrails = [pkg for pkg in packages if is_guardrails_hub_uri(pkg)]
    for guardrail in track(
        guardrails,
        description="Running guardrails post-installation...",
        transient=True,
    ):
        install_guardrail(guardrail)

    console.print("[bold green]Packages successfully added.[/bold green]")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def remove(
    ctx: typer.Context,
    packages: Annotated[
        List[str],
        typer.Argument(
            help="The packages to add, as PEP 508 requirements or Guardrails Hub URIs."
        ),
    ],
):
    """
    Remove dependencies from the project. Works for both Python and Guardrails Hub URIs.

    Execute 'uv remove --help' for more information about uv arguments and options.
    """
    guardrails = [pkg for pkg in packages if is_guardrails_hub_uri(pkg)]
    if guardrails:
        for guardrail in track(
            guardrails,
            description="Uninstalling guardrails...",
            transient=True,
        ):
            uninstall_guardrail(guardrail)

    with console.status("Removing Python dependencies...\n") as status:
        # Resolve python package names (convert hub uris to python packages)
        python_packages = [resolve_python_package(pkg) for pkg in packages]
        # Remove packages from uv
        uv.remove(python_packages, *ctx.args)

        status.update("Removing guardrails...\n")
        with ProjectManager() as project:
            for pkg in guardrails:
                project.remove_guardrail(pkg)

    console.print("[bold green]Packages successfully removed.[/bold green]")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def sync(ctx: typer.Context) -> None:
    """
    Update the project's environment.

    Execute 'uv sync --help' for more information about uv arguments and options.
    """
    with console.status("Fetching guardrails...\n") as status:
        # Get guardrails
        with ProjectManager(read_only=True) as project:
            guardrails = project.guardrails

        status.update("Updating guardrails Python packages...\n")

        # Resolve python package names (convert hub uris to python packages)
        python_packages = [resolve_python_package(pkg) for pkg in guardrails]
        # Add packages to uv
        uv.add(["guardrails-ai"] + python_packages)

        status.update("Syncing Python packages...\n")
        uv.sync(*ctx.args)

    for guardrail in track(
        cast(Iterable, guardrails),
        description="Running guardrails post-installation...",
        transient=True,
    ):
        install_guardrail(guardrail)

    console.print("[bold green]Packages successfully synced.[/bold green]")


if __name__ == "__main__":
    app()
