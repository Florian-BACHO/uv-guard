import os
import subprocess

import pytest

from uv_guard.exceptions import UvGuardException
from uv_guard.guardrails import install, uninstall, configure


def test_configure_calls_subprocess(mocker):
    """
    Test that configure calls subprocess.run with the correct arguments
    and passes through additional args.
    """
    # Arrange
    # Patch subprocess.run inside uv_guard.guardrails
    mock_subprocess_run = mocker.patch("uv_guard.guardrails.subprocess.run")

    # Mock os.environ to ensure we don't rely on the actual system environment for the assertion
    mock_env = {"PATH": "/bin"}
    mocker.patch.dict(os.environ, mock_env, clear=True)

    # Act
    # We pass extra arguments to ensure *args is working
    configure("--token", "123")

    # Assert
    mock_subprocess_run.assert_called_once()

    # Inspect arguments passed to subprocess.run
    call_args = mock_subprocess_run.call_args
    command_arg = call_args[0][0]
    kwargs = call_args[1]

    assert command_arg == ["guardrails", "configure", "--token", "123"]
    assert kwargs["check"] is True
    assert kwargs["stdout"] is None
    assert kwargs["env"] == mock_env


def test_configure_raises_on_missing_executable(mocker):
    """
    Test that UvGuardException is raised when the guardrails executable is not found.
    """
    # Arrange
    mocker.patch("uv_guard.guardrails.subprocess.run", side_effect=FileNotFoundError)

    # Act & Assert
    with pytest.raises(UvGuardException) as excinfo:
        configure()

    assert "Unable to invoke guardrails" in str(excinfo.value)
    assert "uv tool install guardrails" in str(excinfo.value)


def test_configure_raises_on_process_error(mocker):
    """
    Test that UvGuardException is raised when the subprocess exits with a non-zero code.
    """
    # Arrange
    # Simulate a return code of 127
    mock_error = subprocess.CalledProcessError(returncode=127, cmd=["guardrails"])
    mocker.patch("uv_guard.guardrails.subprocess.run", side_effect=mock_error)

    # Act & Assert
    with pytest.raises(UvGuardException) as excinfo:
        configure()

    assert "uv command exited with code 127" in str(excinfo.value)


def test_install(mocker):
    """
    Test that install calls uv.run with the correct arguments.
    """
    # Arrange
    # Patch 'uv_guard.uv.run' because guardrails.py imports 'uv_guard.uv as uv'
    mock_run = mocker.patch("uv_guard.uv.run")
    test_uri = "hub://guardrails/regex_match"

    # Act
    install(test_uri)

    # Assert
    mock_run.assert_called_once_with("guardrails", "hub", "install", test_uri)


def test_uninstall(mocker):
    """
    Test that uninstall calls uv.run with the correct arguments.
    """
    # Arrange
    mock_run = mocker.patch("uv_guard.uv.run")
    test_uri = "hub://guardrails/regex_match"

    # Act
    uninstall(test_uri)

    # Assert
    mock_run.assert_called_once_with("guardrails", "hub", "uninstall", test_uri)
