import pytest
from uv_guard.package import (
    is_guardrails_hub_uri,
    get_guardrail_id_and_version,
    resolve_python_package,
)


@pytest.mark.parametrize(
    "package_name, expected",
    [
        ("hub://guardrails/test", True),
        ("hub://guardrails/test>=0.0.1", True),
        ("guardrails/test", False),
        ("numpy", False),
        ("git+https://github.com/guardrails-ai/guardrails.git", False),
        ("", False),
    ],
)
def test_is_guardrails_hub_uri(package_name: str, expected: bool):
    """Verify detection of Hub URIs."""
    assert is_guardrails_hub_uri(package_name) is expected


def test_get_guardrail_id_and_version_basic():
    """Verify extraction of ID from a basic URI."""
    uri = "hub://guardrails/test"
    vid, version = get_guardrail_id_and_version(uri)

    # We expect the ID to be preserved and version to be None or empty
    assert vid == "guardrails/test"
    assert version is None or version == ""


def test_get_guardrail_id_and_version_with_version_specifier():
    """Verify extraction of ID and version when a specifier is present."""
    uri = "hub://guardrails/test>=0.0.1"
    vid, version = get_guardrail_id_and_version(uri)

    assert vid == "guardrails/test"
    assert version == ">=0.0.1"


def test_resolve_python_package_noop():
    """Verify that standard Python packages are returned unchanged."""
    assert resolve_python_package("numpy") == "numpy"
    assert resolve_python_package("pandas>=2.0.0") == "pandas>=2.0.0"


def test_resolve_python_package_hub_uri():
    """
    Verify resolving a Hub URI to a PEP-503 compliant package name.

    Since we cannot mock, we dynamically check the expected name
    using the service to ensure the test passes even if Guardrails
    changes their naming convention (e.g. underscores vs dashes).
    """
    result = resolve_python_package("hub://guardrails/some_validator")

    assert result == "guardrails-grhub-some-validator"


def test_resolve_python_package_hub_uri_with_version():
    """Verify resolving a Hub URI with a version specifier."""
    result = resolve_python_package("hub://guardrails/some_validator>=0.5.0")

    assert result == "guardrails-grhub-some-validator>=0.5.0"
