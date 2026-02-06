from typing import Tuple

from guardrails.hub.validator_package_service import ValidatorPackageService


def is_guardrails_hub_uri(package: str) -> bool:
    """Check if the given package is a Guardrails-AI Hub URI."""
    return package.startswith("hub://")


def get_guardrail_id_and_version(hub_uri: str) -> Tuple[str, str]:
    """Get the Guardrails-AI Hub ID and package version from the given Hub URI."""
    return ValidatorPackageService.get_validator_id(hub_uri)


def resolve_python_package(package: str) -> str:
    """
    Resolve the given package name to a Python Package URI.
    If 'package' is a Python package, return it without modification.
    If 'package' is a Guardrails-AI Hub URI, return its package URI.
    """
    # Check if the uri is a standard Python package
    if not package.startswith("hub://"):
        return package

    # Resolve Guardrails AI Hub URI to Python package
    validator_id, validator_version = get_guardrail_id_and_version(package)
    pep_503_package_name = ValidatorPackageService.get_normalized_package_name(
        validator_id
    )

    return (
        pep_503_package_name
        if validator_version is None
        else f"{pep_503_package_name}{validator_version}"
    )
