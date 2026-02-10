import pytest
from unittest.mock import MagicMock, call, patch
from typer.testing import CliRunner
from uv_guard.cli import app
from uv_guard.exceptions import UvGuardException

runner = CliRunner()


# --- Fixtures ---


@pytest.fixture
def mock_uv():
    """Mocks the uv_guard.uv module (subprocess calls)."""
    with patch("uv_guard.cli.uv") as mock_uv:
        yield mock_uv


@pytest.fixture
def mock_project_manager():
    """
    Mocks the ProjectManager context manager.
    Returns the instance that would be yielded by 'with ProjectManager() as project:'.

    Includes a reference to .mock_class so constructors can be verified.
    """
    with patch("uv_guard.cli.ProjectManager") as MockPM:
        # Create the mock instance that the context manager yields
        project_instance = MagicMock()

        # Setup the __enter__ to return our mock instance
        MockPM.return_value.__enter__.return_value = project_instance

        # Default behavior: simple pass-through for add_guardrail so tests verify flow
        project_instance.add_guardrail.side_effect = lambda x: x

        # Attach the class mock to the instance so we can check __init__ calls in tests
        project_instance.mock_class = MockPM

        yield project_instance


@pytest.fixture
def mock_guardrails():
    """Mocks the guardrail package."""
    with (
        patch("uv_guard.cli.guardrails_ai") as mock_guardrails_ai,
    ):
        yield mock_guardrails_ai


@pytest.fixture
def mock_resolve_guardrails_token():
    """Mocks the resolve_guardrails_token function."""
    with (
        patch("uv_guard.cli.resolve_guardrails_token") as mock_resolve_guardrails_token,
    ):
        yield mock_resolve_guardrails_token


# --- Tests ---


def test_init_command(mock_uv):
    """Test that 'init' initializes the project and adds guardrails-ai."""
    result = runner.invoke(app, ["init"])

    assert result.exit_code == 0
    assert "Project successfully initialized" in result.stdout

    mock_uv.init.assert_called_once()
    mock_uv.add.assert_called_once_with(["guardrails-ai"], include_index_flags=False)


def test_init_command_with_args(mock_uv):
    """Test that 'init' passes extra arguments to uv init."""
    result = runner.invoke(app, ["init", "--name", "foo", "--no-workspace"])

    assert result.exit_code == 0

    call_args = mock_uv.init.call_args[0]
    assert "--name" in call_args
    assert "foo" in call_args


def test_configure_command(mock_guardrails):
    """Test that 'configure' delegates to guardrails_ai.configure with arguments."""
    result = runner.invoke(
        app, ["configure", "--token", "my-token", "--disable-metrics"]
    )

    assert result.exit_code == 0
    assert "Guardrails AI successfully configured" in result.stdout

    # Verify the underlying configure function was called with the passed arguments
    mock_guardrails.configure.assert_called_once()
    call_args = mock_guardrails.configure.call_args[0]
    assert "--token" in call_args
    assert "my-token" in call_args
    assert "--disable-metrics" in call_args


def test_add_standard_package(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test adding a standard PyPI package."""
    result = runner.invoke(app, ["add", "requests"])

    assert result.exit_code == 0

    # Logic verification
    mock_project_manager.add_guardrail.assert_not_called()
    mock_uv.add.assert_called_once_with(["guardrails-ai", "requests"])
    mock_guardrails.install.assert_not_called()


def test_add_hub_uri(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test adding a Guardrails Hub URI."""
    hub_uri = "hub://guardrails/regex"
    resolved_name = "guardrails-grhub-regex"

    result = runner.invoke(app, ["add", hub_uri])

    assert result.exit_code == 0

    # 1. Project TOML updated
    mock_project_manager.add_guardrail.assert_called_once_with(hub_uri)

    # 2. UV added with resolved name
    mock_uv.add.assert_called_once_with(["guardrails-ai", resolved_name])

    # 3. Post-install hook triggered
    mock_guardrails.install.assert_called_once_with(hub_uri)


def test_add_mixed_args(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test adding a mix of standard packages and hub URIs."""
    args = ["pandas", "hub://guardrails/pii"]

    result = runner.invoke(app, ["add", *args])

    assert result.exit_code == 0

    # Only the hub URI hits the project manager
    mock_project_manager.add_guardrail.assert_called_once_with("hub://guardrails/pii")

    # UV gets both (resolved)
    expected_uv = ["guardrails-ai", "pandas", "guardrails-grhub-pii"]
    mock_uv.add.assert_called_once_with(expected_uv)


def test_remove_command(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test removing a package."""
    hub_uri = "hub://guardrails/junk"
    resolved_name = "guardrails-grhub-junk"

    result = runner.invoke(app, ["remove", hub_uri])

    assert result.exit_code == 0

    # 1. Uninstall hook runs first
    mock_guardrails.uninstall.assert_called_once_with(hub_uri)

    # 2. UV remove runs
    mock_uv.remove.assert_called_once_with([resolved_name])

    # 3. Project TOML cleaned up
    mock_project_manager.remove_guardrail.assert_called_once_with(hub_uri)


def test_sync_command(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test basic syncing behavior."""
    # Setup mock project state
    mock_project_manager.guardrails = ["hub://guardrails/a", "hub://guardrails/b"]

    result = runner.invoke(app, ["sync"])

    assert result.exit_code == 0

    # 1. Verify ProjectManager initialization (default args)
    mock_project_manager.mock_class.assert_called_once_with(
        read_only=True,
        include_all=False,
        include_packages=None,
        exclude_packages=None,
        include_project=True,  # Default since no_install_project is False
    )

    # 2. UV sync called (no extra args passed)
    mock_uv.sync.assert_called_once_with()

    # 3. Install hooks run for the returned guardrails
    assert mock_guardrails.install.call_count == 2
    mock_guardrails.install.assert_has_calls(
        [call("hub://guardrails/a"), call("hub://guardrails/b")]
    )


def test_sync_pass_through_args(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test sync command passes unknown extra args (like --frozen) to uv."""
    mock_project_manager.guardrails = []

    result = runner.invoke(app, ["sync", "--frozen"])

    assert result.exit_code == 0

    # Logic: standard typer args are parsed, unknown args (ctx.args) are preserved
    mock_uv.sync.assert_called_once()
    call_args = mock_uv.sync.call_args[0]
    assert "--frozen" in call_args


def test_sync_with_package_selection(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test sync with specific --package arguments."""
    mock_project_manager.guardrails = ["hub://guardrails/pkg-specific"]

    # We pass two packages
    result = runner.invoke(app, ["sync", "--package", "api", "--package", "core"])

    assert result.exit_code == 0

    # 1. Verify ProjectManager received the filters
    mock_project_manager.mock_class.assert_called_once()
    _, kwargs = mock_project_manager.mock_class.call_args
    assert kwargs["include_packages"] == ["api", "core"]

    # 2. Verify UV received the reconstructed arguments
    mock_uv.sync.assert_called_once()
    args_passed_to_uv = mock_uv.sync.call_args[0]

    # UV args should include --package api --package core
    assert "--package" in args_passed_to_uv
    assert "api" in args_passed_to_uv
    assert "core" in args_passed_to_uv
    assert args_passed_to_uv.count("--package") == 2


def test_sync_with_flags(
    mock_uv, mock_project_manager, mock_guardrails, mock_resolve_guardrails_token
):
    """Test sync with boolean flags like --all-packages and --no-install-project."""
    mock_project_manager.guardrails = []

    result = runner.invoke(app, ["sync", "--all-packages", "--no-install-project"])

    assert result.exit_code == 0

    # 1. Verify ProjectManager received correct bool logic
    mock_project_manager.mock_class.assert_called_once()
    _, kwargs = mock_project_manager.mock_class.call_args

    assert kwargs["include_all"] is True
    assert kwargs["include_project"] is False  # Because no-install-project was True

    # 2. Verify UV received the reconstructed flags
    mock_uv.sync.assert_called_once()
    args_passed_to_uv = mock_uv.sync.call_args[0]

    assert "--all-packages" in args_passed_to_uv
    assert "--no-install-project" in args_passed_to_uv


def test_forward_to_uv_success():
    """
    Test that a forwarded command calls uv.call_uv with the correct
    arguments and specifically quiet=False.
    """
    # Patch where call_uv is defined
    with patch("uv_guard.uv.call_uv") as mock_call_uv:
        # Simulate running: uv-guard lock --upgrade
        result = runner.invoke(app, ["lock", "--upgrade"])

        assert result.exit_code == 0

        # Verify:
        # 1. Command name "lock"
        # 2. Argument "--upgrade"
        # 3. Keyword argument quiet=False
        mock_call_uv.assert_called_once_with("lock", "--upgrade", quiet=False)


def test_forward_to_uv_exception_handling():
    """
    Test that if the underlying uv call fails (raises UvGuardException),
    the CLI catches it, prints the error, and exits with code 1.
    """
    with patch("uv_guard.uv.call_uv") as mock_call_uv:
        # Simulate call_uv raising an exception
        error_message = "Simulated UV failure"
        mock_call_uv.side_effect = UvGuardException(error_message)

        # Invoke a forwarded command
        result = runner.invoke(app, ["lock"])

        # Assert clean exit with error code 1
        assert result.exit_code == 1
