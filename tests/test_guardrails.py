from uv_guard.guardrails import install_guardrail, uninstall_guardrail


def test_install_guardrail(mocker):
    """
    Test that install_guardrail calls uv.run with the correct arguments.
    """
    # Arrange
    # Patch 'uv_guard.uv.run' because guardrails.py imports 'uv_guard.uv as uv'
    mock_run = mocker.patch("uv_guard.uv.run")
    test_uri = "hub://guardrails/regex_match"

    # Act
    install_guardrail(test_uri)

    # Assert
    mock_run.assert_called_once_with("guardrails", "hub", "install", test_uri)


def test_uninstall_guardrail(mocker):
    """
    Test that uninstall_guardrail calls uv.run with the correct arguments.
    """
    # Arrange
    mock_run = mocker.patch("uv_guard.uv.run")
    test_uri = "hub://guardrails/regex_match"

    # Act
    uninstall_guardrail(test_uri)

    # Assert
    mock_run.assert_called_once_with("guardrails", "hub", "uninstall", test_uri)
