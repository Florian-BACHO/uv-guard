from __future__ import annotations

import glob
from typing import cast, Any, MutableMapping, List

import tomlkit
import tomlkit.items
from pathlib import Path


from uv_guard.exceptions import UvGuardException
from uv_guard.package import get_guardrail_id_and_version

GUARDRAILS_INDEX_URL = "https://pypi.guardrailsai.com/simple"
INDEX_NAME = "guardrails-hub"


class ProjectManager:
    """A class to manage the projects.toml file with recursive workspace support."""

    def __init__(
        self,
        path: str | Path = "pyproject.toml",
        read_only: bool = False,
        # Filtering context passed down recursively
        include_all: bool = False,
        include_packages: List[str] | None = None,
        exclude_packages: List[str] | None = None,
        include_project: bool = True,
        _is_root: bool = True,  # Internal flag to track recursion depth
    ) -> None:
        self.path = path if isinstance(path, Path) else Path(path).resolve()

        if not self.path.exists():
            raise UvGuardException(f"pyproject.toml not found at {self.path}")

        self.root_dir = self.path.parent
        self.project_doc: tomlkit.TOMLDocument | None = None
        self.read_only: bool = read_only

        # Filter settings
        self.include_all = include_all
        self.include_packages = set(include_packages or [])
        self.exclude_packages = set(exclude_packages or [])
        self.include_project = include_project
        self._is_root = _is_root

    def __enter__(self) -> ProjectManager:
        try:
            with self.path.open() as file:
                self.project_doc = tomlkit.load(file)
        except Exception:
            raise UvGuardException(f"Error: Could not parse {self.path}.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is not None or self.read_only:
            return

        try:
            with self.path.open("w") as file:
                tomlkit.dump(cast(MutableMapping, self.project_doc), file)
        except Exception:  # pragma: no cover
            raise UvGuardException(f"Error: Could not write {self.path}")

    @property
    def _project_table(self) -> tomlkit.items.Table:
        """Return the project table."""
        doc = cast(Any, self.project_doc)
        if doc is None:
            raise ValueError("project.toml is not loaded.")

        project_table = doc.get("project")
        if project_table is None:
            raise UvGuardException(f'Error: "[project]" not found in {self.path}')
        return project_table

    @property
    def project_name(self) -> str | None:
        """Get the name of the current project."""
        return self._project_table.get("name")

    @property
    def should_include_self(self) -> bool:
        """Determine if this specific project instance's guardrails should be included."""
        name = self.project_name

        # 1. Global Exclusion check
        if name and name in self.exclude_packages:
            return False

        # 2. Root Project Check (controlled by --no-install-project)
        if self._is_root:
            return self.include_project

        # 3. Workspace Member Check
        # Included if --all-packages is set OR if specifically named in --package
        if self.include_all:
            return True
        if name and name in self.include_packages:
            return True

        return False

    @property
    def local_guardrails(self) -> List[str]:
        """Return the guardrails defined strictly in this file."""
        guardrails = self._project_table.get("guardrails")
        if guardrails is None:
            return []
        if isinstance(guardrails, (list, tomlkit.items.Array)):
            return list(guardrails)
        return []

    @property
    def guardrails(self) -> List[str]:
        """
        Recursively fetch guardrails from this project and any workspace members.
        Returns a flat list of unique URIs.
        """
        collected_guardrails = set()

        # 1. Add local guardrails if this project matches filters
        if self.should_include_self:
            collected_guardrails.update(self.local_guardrails)

        # 2. Check for Workspace Members (Recursion)
        doc = cast(Any, self.project_doc)
        tool_uv = doc.get("tool", {}).get("uv", {})
        workspace_members = tool_uv.get("workspace", {}).get("members", [])

        if workspace_members:
            for pattern in workspace_members:
                # Resolve glob relative to this project's directory
                full_pattern = str(self.root_dir / pattern)

                for match in glob.glob(full_pattern, recursive=False):
                    member_path = Path(match) / "pyproject.toml"

                    # Prevent infinite recursion if glob includes self
                    if member_path.resolve() == self.path.resolve():
                        continue

                    if member_path.exists():
                        # RECURSION: Instantiate a new manager for the member
                        # We pass _is_root=False so members know they are dependencies
                        with (
                            ProjectManager(
                                path=member_path,
                                read_only=True,  # Always read-only for children
                                include_all=self.include_all,
                                include_packages=list(self.include_packages),
                                exclude_packages=list(self.exclude_packages),
                                include_project=self.include_project,  # Passed but ignored due to _is_root=False
                                _is_root=False,
                            ) as member_project
                        ):
                            collected_guardrails.update(member_project.guardrails)

        return list(collected_guardrails)

    # --- Mutation methods (add/remove) apply ONLY to the specifically loaded file ---

    @property
    def _mutable_guardrails_array(self) -> tomlkit.items.Array:
        """Helper to get the mutable array for add/remove operations."""
        guardrails = self._project_table.get("guardrails")
        if guardrails is None:
            guardrails = tomlkit.array()
            self._project_table["guardrails"] = guardrails
        return guardrails

    def add_guardrail(self, hub_uri: str) -> str:
        guardrail_id, guardrail_version = get_guardrail_id_and_version(hub_uri)
        guardrails = self._mutable_guardrails_array

        for i in range(len(guardrails)):
            current_id, _ = get_guardrail_id_and_version(guardrails[i])
            if current_id == guardrail_id:
                if guardrail_version is not None:
                    guardrails[i] = hub_uri
                return guardrails[i]

        guardrails.append(hub_uri)
        return hub_uri

    def remove_guardrail(self, hub_uri: str) -> None:
        guardrail_id, _ = get_guardrail_id_and_version(hub_uri)
        guardrails = self._mutable_guardrails_array

        for i in range(len(guardrails)):
            current_id, _ = get_guardrail_id_and_version(guardrails[i])
            if current_id == guardrail_id:
                guardrails.pop(i)
                break
