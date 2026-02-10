import subprocess
from unittest.mock import patch
import pytest
from uv_guard import uv
from uv_guard.exceptions import UvGuardException


# --- Fixtures ---


@pytest.fixture
def mock_resolve_token():
    with patch("uv_guard.uv.resolve_guardrails_token") as mock:
        yield mock


@pytest.fixture
def mock_subprocess_run():
    with patch("uv_guard.uv.subprocess.run") as mock:
        yield mock


@pytest.fixture
def mock_call_uv():
    """Mocks the internal _call_uv function for testing high-level wrappers."""
    with patch("uv_guard.uv.call_uv") as mock:
        yield mock


@pytest.fixture
def mock_resolve_flags():
    """Mocks the internal _resolve_index_flags function."""
    with patch("uv_guard.uv._resolve_index_flags") as mock:
        yield mock


# --- Tests for Internal Helpers ---


def test_resolve_index_flags(mock_resolve_token):
    """Test that index flags are constructed correctly with the token."""
    mock_resolve_token.return_value = "secret_token_123"

    flags = uv._resolve_index_flags()

    assert len(flags) == 2
    assert (
        flags[0]
        == "--index=https://__token__:secret_token_123@pypi.guardrailsai.com/simple"
    )
    assert flags[1] == "--default-index=https://pypi.org/simple"
    mock_resolve_token.assert_called_once()


def test_call_uv_success(mock_subprocess_run):
    """Test that call_uv invokes subprocess.run with correct args and env (Quiet Mode)."""

    # Execute (quiet defaults to True)
    uv.call_uv("some_cmd", "arg1", "--flag")

    # Verify
    assert mock_subprocess_run.called
    args, kwargs = mock_subprocess_run.call_args

    # Check command structure
    cmd_list = args[0]
    # Update: In your code, `*args` are added before `--quiet` is appended.
    assert cmd_list == ["uv", "some_cmd", "--quiet", "arg1", "--flag"]

    # Check environment variables
    env_arg = kwargs.get("env")
    assert env_arg is not None
    assert env_arg["PYTHONIOENCODING"] == "utf-8"
    assert env_arg["LANG"] == "C.UTF-8"

    # Check standard kwargs
    assert kwargs["check"] is True
    assert kwargs["stdout"] == subprocess.DEVNULL


def test_call_uv_not_quiet(mock_subprocess_run):
    """Test that call_uv handles quiet=False correctly."""

    # Execute
    uv.call_uv("some_cmd", "arg1", quiet=False)

    # Verify
    assert mock_subprocess_run.called
    args, kwargs = mock_subprocess_run.call_args

    # Check command structure: Should NOT have --quiet
    cmd_list = args[0]
    assert cmd_list == ["uv", "some_cmd", "arg1"]

    # Check stdout: Should default to None (inherit from parent) when not quiet
    assert kwargs["stdout"] is None


def test_call_uv_file_not_found(mock_subprocess_run):
    """Test handling when 'uv' executable is missing."""
    mock_subprocess_run.side_effect = FileNotFoundError()

    with pytest.raises(UvGuardException):
        uv.call_uv("init")


def test_call_uv_process_error(mock_subprocess_run):
    """Test handling when 'uv' returns a non-zero exit code."""
    # Simulate uv failing with error code 127
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(127, ["uv"])

    with pytest.raises(UvGuardException):
        uv.call_uv("init")


# --- Tests for Public Command Wrappers ---


def test_init(mock_call_uv):
    """Test the init command wrapper."""
    uv.init("arg1", "arg2")
    mock_call_uv.assert_called_once_with("init", "arg1", "arg2")


def test_add(mock_call_uv, mock_resolve_flags):
    """Test the add command wrapper injects index flags."""
    mock_resolve_flags.return_value = ["--index=custom", "--default=pypi"]
    packages = ["numpy", "pandas"]
    extra_args = ("--dev",)

    uv.add(packages, *extra_args)

    # Arguments should be: command, *packages, *index_flags, *args
    mock_call_uv.assert_called_once_with(
        "add", "numpy", "pandas", "--index=custom", "--default=pypi", "--dev"
    )


def test_add_no_flags(mock_call_uv, mock_resolve_flags):
    """Test the add command wrapper when include_index_flags is False."""
    packages = ["numpy"]

    uv.add(packages, include_index_flags=False)

    # Should not resolve flags or include them
    mock_resolve_flags.assert_not_called()
    mock_call_uv.assert_called_once_with("add", "numpy")


def test_remove(mock_call_uv):
    """Test the remove command wrapper."""
    packages = ["numpy"]
    uv.remove(packages, "--force")
    mock_call_uv.assert_called_once_with("remove", "numpy", "--force")


def test_run(mock_call_uv):
    """Test the run command wrapper (default quiet)."""
    uv.run("script.py", "--verbose")
    # Update: run passes quiet=quiet (defaults to True)
    mock_call_uv.assert_called_once_with("run", "script.py", "--verbose", quiet=True)


def test_run_not_quiet(mock_call_uv):
    """Test the run command wrapper with quiet=False."""
    uv.run("script.py", quiet=False)
    mock_call_uv.assert_called_once_with("run", "script.py", quiet=False)


def test_sync(mock_call_uv, mock_resolve_flags):
    """Test the sync command wrapper injects index flags."""
    mock_resolve_flags.return_value = ["--index=custom"]

    uv.sync("--all-extras")

    # Arguments should be: command, *index_flags, *args
    mock_call_uv.assert_called_once_with("sync", "--index=custom", "--all-extras")
