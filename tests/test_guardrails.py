from uv_guard.guardrails import install, uninstall, configure


def test_configure(mocker):
    """
    Test that configure calls uv.run with the correct arguments.
    """
    # Arrange
    # Patch 'uv_guard.uv.run' because guardrails.py imports 'uv_guard.uv as uv'
    mock_run = mocker.patch("uv_guard.uv.run")

    # Act
    configure()

    # Assert
    mock_run.assert_called_once_with("guardrails", "configure", quiet=False)


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
