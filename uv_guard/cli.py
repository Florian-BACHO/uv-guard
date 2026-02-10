from typing import Annotated, List, cast, Iterable

import typer

from rich.progress import track

from uv_guard.exceptions import UvGuardException
from uv_guard.package import resolve_python_package, is_guardrails_hub_uri
import uv_guard.guardrails as guardrails_ai
from uv_guard.project import ProjectManager
from uv_guard.logs import console, error_console
import uv_guard.uv as uv
from uv_guard.token import resolve_guardrails_token

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
    try:
        with console.status("Initializing project...\n") as status:
            uv.init(*ctx.args)

            status.update("Installing guardrails-ai...\n")
            uv.add(["guardrails-ai"], include_index_flags=False)
    except UvGuardException as e:
        error_console.print(e)
        raise typer.Exit(1)

    console.print("[bold green]Project successfully initialized.[/bold green]")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def configure(
    ctx: typer.Context,
) -> None:
    """
    Configure Guardrails AI.

    Execute 'guardrails configure --help' for more information about guardrails arguments and options.
    """
    try:
        guardrails_ai.configure(*ctx.args)
    except UvGuardException as e:
        error_console.print(e)
        raise typer.Exit(1)

    console.print("[bold green]Guardrails AI successfully configured.[/bold green]")


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
    try:
        # Check for Guardrails Hub token
        resolve_guardrails_token()

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
            guardrails_ai.install(guardrail)
    except UvGuardException as e:
        error_console.print(e)
        raise typer.Exit(1)

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
    try:
        # Check for Guardrails Hub token
        resolve_guardrails_token()

        guardrails = [pkg for pkg in packages if is_guardrails_hub_uri(pkg)]
        if guardrails:
            for guardrail in track(
                guardrails,
                description="Uninstalling guardrails...",
                transient=True,
            ):
                guardrails_ai.uninstall(guardrail)

        with console.status("Removing Python dependencies...\n") as status:
            # Resolve python package names (convert hub uris to python packages)
            python_packages = [resolve_python_package(pkg) for pkg in packages]
            # Remove packages from uv
            uv.remove(python_packages, *ctx.args)

            status.update("Removing guardrails...\n")
            with ProjectManager() as project:
                for pkg in guardrails:
                    project.remove_guardrail(pkg)
    except UvGuardException as e:
        error_console.print(e)
        raise typer.Exit(1)

    console.print("[bold green]Packages successfully removed.[/bold green]")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def sync(
    ctx: typer.Context,
    all_packages: bool = typer.Option(
        False, "--all-packages", help="Sync all packages in the workspace."
    ),
    package: List[str] | None = typer.Option(
        None, "--package", help="Sync for specific packages in the workspace."
    ),
    no_install_project: bool = typer.Option(
        False, "--no-install-project", help="Do not install the current project."
    ),
    no_install_workspace: bool = typer.Option(
        False,
        "--no-install-workspace",
        help="Do not install any workspace members, including the root project.",
    ),
    no_install_package: List[str] | None = typer.Option(
        None, "--no-install-package", help="Do not install the given package(s)."
    ),
) -> None:
    """
    Update the project's environment.

    Execute 'uv sync --help' for more information about uv arguments and options.
    """
    try:
        uv_args = list(ctx.args)

        if all_packages:
            uv_args.append("--all-packages")

        if no_install_project:
            uv_args.append("--no-install-project")

        if no_install_workspace:
            uv_args.append("--no-install-workspace")

        if package:
            for p in package:
                uv_args.extend(["--package", p])

        if no_install_package:
            for p in no_install_package:
                uv_args.extend(["--no-install-package", p])

        # Check for Guardrails Hub token
        resolve_guardrails_token()

        with console.status("Fetching guardrails...\n") as status:
            # Get guardrails
            with ProjectManager(
                read_only=True,
                include_all=all_packages,
                include_packages=package,
                exclude_packages=no_install_package,
                include_project=not no_install_project,
            ) as project:
                guardrails = project.guardrails

            status.update("Syncing Python packages...\n")
            uv.sync(*uv_args)

        for guardrail in track(
            cast(Iterable, guardrails),
            description="Running guardrails post-installation...",
            transient=True,
        ):
            guardrails_ai.install(guardrail)
    except UvGuardException as e:
        error_console.print(e)
        raise typer.Exit(1)

    console.print("[bold green]Packages successfully synced.[/bold green]")


# ---------- Unimplemented commands (forward to uv) ----------


def forward_to_uv(ctx: typer.Context) -> None:
    """Forward the command to uv."""
    if ctx.command.name is None:
        error_console.print("Missing command.")
        raise typer.Exit(1)

    try:
        uv.call_uv(ctx.command.name, *ctx.args, quiet=False)
    except UvGuardException as e:
        error_console.print(e)
        raise typer.Exit(1)


UNIMPLEMENTED_COMMANDS = [
    {
        "name": "auth",
        "help": "Manage authentication.",
    },
    {
        "name": "lock",
        "help": "Update the project's lockfile.",
    },
    {
        "name": "export",
        "help": "Export the project's lockfile to an alternate format.",
    },
    {
        "name": "tree",
        "help": "Display the project's dependency tree.",
    },
    {
        "name": "format",
        "help": "Format Python code in the project.",
    },
    {
        "name": "tool",
        "help": "Run and install commands provided by Python packages.",
    },
    {
        "name": "python",
        "help": "Manage Python versions and installations.",
    },
    {
        "name": "pip",
        "help": "Manage Python packages with a pip-compatible interface.",
    },
    {
        "name": "venv",
        "help": "Create a virtual environment.",
    },
    {
        "name": "build",
        "help": "Build Python packages into source distributions and wheels.",
    },
    {
        "name": "publish",
        "help": "Upload distributions to an index.",
    },
    {
        "name": "cache",
        "help": "Manage uv's cache.",
    },
    {
        "name": "self",
        "help": "Manage the uv executable.",
    },
]


def add_unimplemented_commands():
    """Add all unimplemented uv commands to the CLI."""
    for command in UNIMPLEMENTED_COMMANDS:
        app.command(
            context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
            name=command["name"],
            help=f"{command['help']}\n\nExecute 'uv {command['name']} --help' for more information about uv "
            f"arguments and options.",
        )(forward_to_uv)


add_unimplemented_commands()

if __name__ == "__main__":
    app()
