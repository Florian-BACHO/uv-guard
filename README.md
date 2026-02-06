# uv-guard

**uv-guard** is a CLI tool that harmonizes the [uv](https://docs.astral.sh/uv/) package manager with the [Guardrails AI](https://guardrailsai.com/) ecosystem.

While `uv` excels at strict environment locking, its synchronization process often identifies and removes Guardrails' static assets as extraneous files. **uv-guard** resolves this conflict by wrapping both tools into a unified workflow. It maintains a persistent record of installed validators, tracks their dependencies, and automatically triggers post-installation scripts whenever the environment is updated—ensuring your validation logic remains intact without manual intervention.

### Configuration & Persistence

To track Guardrails Hub URIs, **uv-guard** extends the standard `pyproject.toml` configuration. When a validator is added, `uv-guard` creates a dedicated `guardrails` list within the configuration file, functioning alongside standard dependencies.

This ensures that the `pyproject.toml` file remains the project's source of truth, tracking both standard Python packages and Guardrails Hub URIs in one place.

**Example `pyproject.toml` structure:**

```toml
[project]
name = "my-project"
dependencies = [
    "guardrails-ai",
    "guardrails-grhub-regex-match",  # The underlying Python package resolved by uv-guard
]
# uv-guard tracks the specific Hub URIs here
guardrails = [
    "hub://guardrails/regex_match"
]
```

## Prerequisites

- **Python**: 3.10+
- **uv**: See the [uv installation page](https://docs.astral.sh/uv/getting-started/installation/)

## Installation

You can install `uv-guard` using `pip`, `pipx`, or `uv tool`:

```bash
# Recommended: Install as a standalone tool via uv
uv tool install uv-guard
```

## Usage

`uv-guard` mirrors the `uv` commands but extends them to support Guardrails Hub URIs (`hub://`).

### Initialize a Project
Initializes a new `uv` project and automatically adds the `guardrails-ai` core dependency.

```bash
uv-guard init
```
The command passes all arguments and options to `uv init`. For example:
```bash
uv-guard init --name my-project
```
forwards the `--name my-project` option.

### Add Dependencies
Adds a package to the project. This command intelligently handles both standard PyPI packages and Guardrails Hub URIs.

When adding a Guardrails Hub URI:
1. It adds the URI to the `guardrails` list in `pyproject.toml`.
2. It resolves the underlying Python package required by the validator and adds it to the standard `dependencies`.
3. It executes the Guardrails post-installation script to set up the validator.

```bash
# Add a standard Python package
uv-guard add pandas

# Add a Guardrails validator
uv-guard add hub://guardrails/regex_match
```
*Passes all standard arguments to `uv add`.*

### Remove Dependencies
Uninstall the guardrails, removes the package from the `uv` environment and cleans up the `pyproject.toml`.

```bash
uv-guard remove hub://guardrails/regex_match
```
*Passes all standard arguments to `uv remove`.*

### Sync Environment
Updates the project environment. This is the critical operation that ensures compatibility.

When syncing, `uv-guard`:
1. Reads the `guardrails` list from `pyproject.toml`.
2. Ensures underlying Python packages are present in the `uv` dependency tree.
3. Executes `uv sync` to update the environment.
4. Re-runs Guardrails installation scripts to restore any assets removed during the sync process.

```bash
uv-guard sync
```
*Passes all standard arguments to `uv sync`.*
