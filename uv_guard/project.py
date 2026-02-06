from __future__ import annotations

from typing import cast, Any, MutableMapping

import tomlkit
import tomlkit.items
from pathlib import Path


from uv_guard.exceptions import UvGuardException
from uv_guard.package import get_guardrail_id_and_version

GUARDRAILS_INDEX_URL = "https://pypi.guardrailsai.com/simple"
INDEX_NAME = "guardrails-hub"


class ProjectManager:
    """A class to manage the projects.toml file."""

    def __init__(
        self, path: str | Path = "pyproject.toml", read_only: bool = False
    ) -> None:
        self.path = path if isinstance(path, Path) else Path(path)

        if not self.path.exists():
            raise UvGuardException("pyproject.toml not found.")

        self.project_doc: tomlkit.TOMLDocument | None = None
        self.read_only: bool = read_only

    def __enter__(self) -> ProjectManager:
        """Load the project.toml file."""
        # Load the project TOML
        try:
            with self.path.open() as file:
                self.project_doc = tomlkit.load(file)
        except Exception:
            raise UvGuardException(f"Error: Could not parse {self.path}.")

        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Save the project.toml file if not read-only."""
        # Skip saving if an exception occurred or if the project manager is read-only
        if exc_type is not None or self.read_only:
            return

        # Save the project TOML changes
        try:
            with self.path.open("w") as file:
                tomlkit.dump(cast(MutableMapping, self.project_doc), file)
        except Exception:
            raise UvGuardException(f"Error: Could not write {self.path}:")

    @property
    def _project_table(self) -> tomlkit.items.Table:
        """Return the project table."""
        doc = cast(Any, self.project_doc)

        if doc is None:
            raise ValueError(
                "project.toml is not loaded. Please, use the ProjectManager within a context manager."
            )

        project_table = doc.get("project")

        if project_table is None or not isinstance(project_table, tomlkit.items.Table):
            raise UvGuardException('Error: "[project]" not found in {self.path}')

        return project_table

    @property
    def guardrails(self) -> tomlkit.items.Array:
        """Return the guardrails URIs."""
        guardrails = self._project_table.get("guardrails")

        if guardrails is None:
            guardrails = tomlkit.array()
            self._project_table["guardrails"] = guardrails

            return guardrails
        elif not isinstance(guardrails, tomlkit.items.Array):
            raise UvGuardException(
                f'Error: "guardrails" is not an array in {self.path}'
            )

        return guardrails.multiline(True)

    def add_guardrail(self, hub_uri: str) -> str:
        """Add or update a guardrails URI."""
        guardrail_id, guardrail_version = get_guardrail_id_and_version(hub_uri)

        guardrails = self.guardrails
        for i in range(len(guardrails)):
            current_id, current_version = get_guardrail_id_and_version(guardrails[i])

            # Skip if the guardrail is not the same as the one being added
            if current_id != guardrail_id:
                continue

            # Replace the existing guardrails if the version is specified
            if guardrail_version is not None:
                guardrails[i] = hub_uri

            # Stop if the guardrail already exists
            return guardrails[i]

        # Append the new guardrails it does not already exist
        guardrails.append(hub_uri)

        return hub_uri

    def remove_guardrail(self, hub_uri: str) -> None:
        """Remove a guardrails URI."""
        guardrail_id, _ = get_guardrail_id_and_version(hub_uri)

        guardrails = self.guardrails
        for i in range(len(guardrails)):
            current_id, _ = get_guardrail_id_and_version(guardrails[i])

            if current_id == guardrail_id:
                guardrails.pop(i)
                break
