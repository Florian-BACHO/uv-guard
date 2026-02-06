import pytest

from uv_guard.exceptions import UvGuardException
from uv_guard.token import resolve_guardrails_token


def test_resolve_guardrails_token_success(mocker):
    """
    Test that the token is returned when it exists in settings.
    """
    # Mock guardrails settings
    # We patch the source object so the import in the function sees the mock
    mock_settings = mocker.patch("uv_guard.token.settings")
    mock_settings.rc.token = "valid-token-123"

    # Run function
    result = resolve_guardrails_token()

    # Assertions
    assert result == "valid-token-123"


def test_resolve_guardrails_token_missing(mocker):
    """
    Test that the function prints an error and raises typer.Exit
    when the token is None.
    """
    # Mock guardrails settings to return None for the token
    mock_settings = mocker.patch("uv_guard.token.settings")
    mock_settings.rc.token = None

    # Run function and expect typer.Exit exception
    with pytest.raises(UvGuardException):
        resolve_guardrails_token()
