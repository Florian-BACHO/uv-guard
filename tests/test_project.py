import pytest
import typer
import tomlkit
import tomlkit.items

from uv_guard.project import ProjectManager


# -----------------------------------------------------------------------------
# Fixtures and Helpers
# -----------------------------------------------------------------------------


@pytest.fixture
def clean_project_toml(tmp_path):
    """Creates a valid, basic pyproject.toml in a temp directory."""
    content = """
    [project]
    name = "test-project"
    version = "0.1.0"
    """
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text(content, encoding="utf-8")
    return toml_path


# -----------------------------------------------------------------------------
# Initialization & Context Manager Tests
# -----------------------------------------------------------------------------


def test_init_file_not_found(tmp_path):
    """Test that initialization fails if the file doesn't exist."""
    non_existent = tmp_path / "missing.toml"

    with pytest.raises(typer.Exit) as exc:
        ProjectManager(path=non_existent)

    assert exc.value.exit_code == 1


def test_context_manager_load_and_save(clean_project_toml):
    """Test that the context manager loads and saves changes."""
    with ProjectManager(path=clean_project_toml) as project:
        # Modify the document directly to test saving
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

    # It initializes fine (checks existence), but fails on __enter__
    manager = ProjectManager(path=bad_toml)

    with pytest.raises(typer.Exit) as exc:
        with manager:
            pass

    assert exc.value.exit_code == 1


# -----------------------------------------------------------------------------
# Property Access Tests
# -----------------------------------------------------------------------------


def test_project_table_missing(tmp_path):
    """Test error when [project] table is missing."""
    toml_path = tmp_path / "pyproject.toml"
    toml_path.write_text("[tool.something]\nfoo='bar'", encoding="utf-8")

    with pytest.raises(typer.Exit) as exc:
        with ProjectManager(path=toml_path) as project:
            _ = project.guardrails

    assert exc.value.exit_code == 1


def test_guardrails_create_if_missing(clean_project_toml):
    """Test that the guardrails array is created if it doesn't exist."""
    with ProjectManager(path=clean_project_toml) as project:
        gr = project.guardrails
        assert isinstance(gr, tomlkit.items.Array)
        assert len(gr) == 0

        # Add something to ensure it saves
        gr.append("hub/test")

    # Verify persistence
    content = clean_project_toml.read_text()
    assert (
        'guardrails = ["hub/test"]' in content
        or 'guardrails = [\n    "hub/test",\n]' in content
    )


def test_guardrails_not_an_array(clean_project_toml):
    """Test error when guardrails exists but is not an array."""
    # Corrupt the file
    content = clean_project_toml.read_text()
    clean_project_toml.write_text(
        content + "\nguardrails = 'string_value'", encoding="utf-8"
    )

    with pytest.raises(typer.Exit) as exc:
        with ProjectManager(path=clean_project_toml) as project:
            _ = project.guardrails

    assert exc.value.exit_code == 1


# -----------------------------------------------------------------------------
# Add/Remove Guardrails Logic
# -----------------------------------------------------------------------------


def test_add_guardrail_new(clean_project_toml):
    """Test adding a new guardrail."""
    with ProjectManager(path=clean_project_toml) as project:
        result = project.add_guardrail("hub://guardrails/new-guard")
        assert result == "hub://guardrails/new-guard"
        assert len(project.guardrails) == 1
        assert project.guardrails[0] == "hub://guardrails/new-guard"


def test_add_guardrail_skip_duplicate(clean_project_toml):
    """Test adding a guardrail that already exists (same version or no version)."""
    with ProjectManager(path=clean_project_toml) as project:
        project.guardrails.append("hub://guardrails/existing")

        # Add same one
        result = project.add_guardrail("hub://guardrails/existing")

        assert len(project.guardrails) == 1
        # Should return the existing one
        assert result == "hub://guardrails/existing"


def test_add_guardrail_update_version(clean_project_toml):
    """Test updating an existing guardrail with a specific version."""
    with ProjectManager(path=clean_project_toml) as project:
        project.guardrails.append("hub://guardrails/existing")

        # Update with version
        result = project.add_guardrail("hub://guardrails/existing:v0.2.0")

        assert len(project.guardrails) == 1
        assert project.guardrails[0] == "hub://guardrails/existing:v0.2.0"
        assert result == "hub://guardrails/existing:v0.2.0"


def test_add_guardrail_no_downgrade_implicit(clean_project_toml):
    """
    Test logic: If existing has version, and we add one WITHOUT version,
    it should essentially return the existing one (skip replacement)
    because `guardrail_version` is None in the input.
    """
    with ProjectManager(path=clean_project_toml) as project:
        project.guardrails.append("hub://guardrails/existing:v0.1.0")

        # Add without version
        project.add_guardrail("hub://guardrails/existing")

        assert len(project.guardrails) == 1
        # Should keep the specific version
        assert project.guardrails[0] == "hub://guardrails/existing:v0.1.0"


def test_remove_guardrail_success(clean_project_toml):
    """Test removing an existing guardrail."""
    with ProjectManager(path=clean_project_toml) as project:
        project.guardrails.append("hub://guardrails/keep-me")
        project.guardrails.append("hub://guardrails/remove-me:v1")

        project.remove_guardrail("hub://guardrails/remove-me")

        assert len(project.guardrails) == 1
        assert project.guardrails[0] == "hub://guardrails/keep-me"


def test_remove_guardrail_not_found(clean_project_toml):
    """Test removing a guardrail that doesn't exist does nothing."""
    with ProjectManager(path=clean_project_toml) as project:
        project.guardrails.append("hub://guardrails/keep-me")

        project.remove_guardrail("hub://guardrails/ghost")

        assert len(project.guardrails) == 1
        assert project.guardrails[0] == "hub://guardrails/keep-me"


def test_usage_without_context_manager(clean_project_toml):
    """Test that accessing properties without __enter__ raises ValueError."""
    manager = ProjectManager(path=clean_project_toml)

    with pytest.raises(ValueError) as exc:
        _ = manager._project_table

    assert "project.toml is not loaded" in str(exc.value)
