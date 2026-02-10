import pytest
import tomlkit
import tomlkit.items

from uv_guard.exceptions import UvGuardException
from uv_guard.project import ProjectManager


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
def clean_project_toml(tmp_path):
    """Creates a valid, basic pyproject.toml in a temp directory."""
    content = """
    [project]
    name = "root-project"
    version = "0.1.0"
    """
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text(content, encoding="utf-8")
    return toml_path


@pytest.fixture
def workspace_setup(tmp_path):
    """
    Creates a workspace structure:
    /pyproject.toml (root, has guardrail 'root-guard')
    /packages/pkg-a/pyproject.toml (member, has guardrail 'pkg-a-guard')
    /packages/pkg-b/pyproject.toml (member, has guardrail 'pkg-b-guard')
    """
    # Root
    root_content = """
    [project]
    name = "root-project"
    version = "0.1.0"
    guardrails = ["hub://root-guard"]

    [tool.uv.workspace]
    members = ["packages/*"]
    """
    (tmp_path / "pyproject.toml").write_text(root_content, encoding="utf-8")

    # Package A
    pkg_a = tmp_path / "packages" / "pkg-a"
    pkg_a.mkdir(parents=True)
    (pkg_a / "pyproject.toml").write_text(
        """
    [project]
    name = "pkg-a"
    version = "0.1.0"
    guardrails = ["hub://pkg-a-guard"]
    """,
        encoding="utf-8",
    )

    # Package B
    pkg_b = tmp_path / "packages" / "pkg-b"
    pkg_b.mkdir(parents=True)
    (pkg_b / "pyproject.toml").write_text(
        """
    [project]
    name = "pkg-b"
    version = "0.1.0"
    guardrails = ["hub://pkg-b-guard"]
    """,
        encoding="utf-8",
    )

    return tmp_path / "pyproject.toml"


# -----------------------------------------------------------------------------
# Initialization & Context Manager Tests
# -----------------------------------------------------------------------------


def test_init_file_not_found(tmp_path):
    """Test that initialization fails if the file doesn't exist."""
    non_existent = tmp_path / "missing.toml"
    with pytest.raises(UvGuardException):
        ProjectManager(path=non_existent)


def test_context_manager_load_and_save(clean_project_toml):
    """Test that the context manager loads and saves changes."""
    with ProjectManager(path=clean_project_toml) as project:
        # Access the raw document to verify save mechanics
        project.project_doc["project"]["description"] = "New Description"  # type: ignore

    # Verify write
    content = clean_project_toml.read_text()
    doc = tomlkit.parse(content)
    assert doc["project"]["description"] == "New Description"  # type: ignore


def test_context_manager_read_only(clean_project_toml):
    """Test that read_only=True prevents saving changes."""
    with ProjectManager(path=clean_project_toml, read_only=True) as project:
        project.project_doc["project"]["description"] = "Should Not Save"  # type: ignore

    # Verify NOT written
    content = clean_project_toml.read_text()
    doc = tomlkit.parse(content)
    assert "description" not in doc["project"]  # type: ignore


def test_context_manager_invalid_toml(tmp_path):
    """Test handling of invalid TOML content."""
    bad_toml = tmp_path / "bad.toml"
    bad_toml.write_text("key = [unclosed array", encoding="utf-8")

    # Init allows existence check, context manager does parsing
    manager = ProjectManager(path=bad_toml)
    with pytest.raises(UvGuardException):
        with manager:
            pass


# -----------------------------------------------------------------------------
# Property Access & Local Mutation Tests
# -----------------------------------------------------------------------------


def test_project_table_missing(tmp_path):
    """Test error when [project] table is missing."""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text("[tool.something]\nfoo='bar'", encoding="utf-8")

    with pytest.raises(UvGuardException):
        with ProjectManager(path=toml_path) as project:
            _ = project.local_guardrails


def test_guardrails_creation_on_add(clean_project_toml):
    """
    Test that the guardrails array is created in the file
    only when we explicitly add a guardrail.
    """
    with ProjectManager(path=clean_project_toml) as project:
        # Initial state: empty list, no array in file yet
        assert project.guardrails == []

        # Add something
        project.add_guardrail("hub://test-guard")

    # Verify persistence
    content = clean_project_toml.read_text()
    assert 'guardrails = ["hub://test-guard"]' in content or "guardrails" in content


# -----------------------------------------------------------------------------
# Add/Remove Guardrails Logic (Local File)
# -----------------------------------------------------------------------------


def test_add_guardrail_new(clean_project_toml):
    """Test adding a new guardrail."""
    with ProjectManager(path=clean_project_toml) as project:
        result = project.add_guardrail("hub://new-guard")
        assert result == "hub://new-guard"

        # Check aggregated list matches
        assert "hub://new-guard" in project.guardrails


def test_add_guardrail_skip_duplicate(clean_project_toml):
    """Test adding a guardrail that already exists."""
    with ProjectManager(path=clean_project_toml) as project:
        project.add_guardrail("hub://existing")

        # Add same one again
        result = project.add_guardrail("hub://existing")

        assert len(project.guardrails) == 1
        assert result == "hub://existing"


def test_add_guardrail_update_version(clean_project_toml):
    """Test updating an existing guardrail with a specific version."""
    with ProjectManager(path=clean_project_toml) as project:
        project.add_guardrail("hub://existing")

        # Update with version
        result = project.add_guardrail("hub://existing:v0.2.0")

        assert "hub://existing:v0.2.0" in project.guardrails
        assert result == "hub://existing:v0.2.0"


def test_remove_guardrail_success(clean_project_toml):
    """Test removing an existing guardrail."""
    with ProjectManager(path=clean_project_toml) as project:
        project.add_guardrail("hub://keep-me")
        project.add_guardrail("hub://remove-me:v1")

        project.remove_guardrail("hub://remove-me")

        assert "hub://keep-me" in project.guardrails
        assert "hub://remove-me:v1" not in project.guardrails


def test_remove_guardrail_not_found(clean_project_toml):
    """Test removing a guardrail that doesn't exist does nothing."""
    with ProjectManager(path=clean_project_toml) as project:
        project.add_guardrail("hub://keep-me")
        project.remove_guardrail("hub://ghost")
        assert len(project.guardrails) == 1


# -----------------------------------------------------------------------------
# Workspace & Filtering Tests (New Recursion Logic)
# -----------------------------------------------------------------------------


def test_workspace_default_root_only(workspace_setup):
    """By default, only the root project's guardrails are fetched."""
    with ProjectManager(path=workspace_setup) as project:
        gr = project.guardrails

        assert "hub://root-guard" in gr
        assert "hub://pkg-a-guard" not in gr
        assert "hub://pkg-b-guard" not in gr


def test_workspace_include_all(workspace_setup):
    """With include_all=True, it should recursively fetch all guardrails."""
    with ProjectManager(path=workspace_setup, include_all=True) as project:
        gr = project.guardrails

        assert "hub://root-guard" in gr
        assert "hub://pkg-a-guard" in gr
        assert "hub://pkg-b-guard" in gr


def test_workspace_specific_package(workspace_setup):
    """With include_packages=['pkg-a'], only root and pkg-a should be present."""
    with ProjectManager(path=workspace_setup, include_packages=["pkg-a"]) as project:
        gr = project.guardrails

        assert "hub://root-guard" in gr
        assert "hub://pkg-a-guard" in gr
        assert "hub://pkg-b-guard" not in gr


def test_workspace_no_install_project(workspace_setup):
    """
    With include_project=False (mapping to --no-install-project),
    root guardrails should be ignored.
    """
    # Case 1: Just root disabled, no other packages requested -> Empty result
    with ProjectManager(path=workspace_setup, include_project=False) as project:
        assert project.guardrails == []

    # Case 2: Root disabled, but --all-packages requested
    with ProjectManager(
        path=workspace_setup, include_project=False, include_all=True
    ) as project:
        gr = project.guardrails
        assert "hub://root-guard" not in gr
        assert "hub://pkg-a-guard" in gr
        assert "hub://pkg-b-guard" in gr


def test_workspace_exclude_package(workspace_setup):
    """Test exclude_packages (e.g. user passes --no-install-package)."""
    with ProjectManager(
        path=workspace_setup, include_all=True, exclude_packages=["pkg-b"]
    ) as project:
        gr = project.guardrails

        assert "hub://root-guard" in gr
        assert "hub://pkg-a-guard" in gr
        assert "hub://pkg-b-guard" not in gr


def test_workspace_recursion_integrity(workspace_setup):
    """Ensure recursion doesn't crash or loop infinitely."""
    # The fixture sets up a clean tree.
    # If the logic in _get_workspace_members_paths incorrectly included root,
    # this might stack overflow.
    with ProjectManager(path=workspace_setup, include_all=True) as project:
        assert len(project.guardrails) == 3
