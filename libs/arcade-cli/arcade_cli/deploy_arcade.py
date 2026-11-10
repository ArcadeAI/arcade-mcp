"""The deploy config and pre-upload checks of an Arcade server deploy.

An Arcade server (a project that depends on arcade-mcp) reads the same deploy config as an
MCP server, ``[tool.arcade.deploy]`` in pyproject.toml or ``[deploy]`` in arcade.toml, and
gets the same checks before anything is uploaded: what the runner can install, which
dependencies lack a prebuilt wheel, and a virtual environment to run the server in locally.

Only ``environment`` and ``secrets`` apply to an Arcade server. They go in the deploy request
as the deployment's environment and secrets, beside the per-call project secrets its tools
declare with ``requires_secrets``. A project with no deploy config sends neither, so it
deploys as it did before the config existed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from arcade_cli.console import console
from arcade_cli.deploy import DeployRefusedError, deployment_runners
from arcade_cli.deploy_checks import check_project
from arcade_cli.deploy_config import (
    DeclaredValues,
    DeployConfig,
    load_deploy_config,
    resolve_declared_values,
    runner_settings_json,
)
from arcade_cli.deploy_mcp import (
    project_python,
    refuse_skipping_declared_secrets,
    warn_about_missing_wheels,
)

# Settings for an MCP server's start and sign-in: an Arcade server starts from --entrypoint
# and the Engine calls it through the Arcade worker API.
_MCP_ONLY_SETTINGS = ("command", "path", "api_key", "oauth_client")


@dataclass(frozen=True)
class ArcadeDeploy:
    """What an Arcade server deploy adds to the request, from the project's deploy config."""

    config: DeployConfig
    # None when the project has no deploy config: the request carries no environment or
    # secrets, as before.
    values: DeclaredValues | None
    # The project's interpreter for the local check; None with --skip-validate.
    python: Path | None

    @property
    def local_environment(self) -> dict[str, str]:
        """The declared environment and secrets, for the server run locally."""
        if self.values is None:
            return {}
        return {**self.values.environment, **self.values.secrets}

    @property
    def runner_settings(self) -> str | None:
        """The contents of ``.arcade/deploy.json``, or ``None`` when the runner needs nothing."""
        return runner_settings_json(self.config)

    def project_secrets(self, names: set[str]) -> set[str]:
        """The per-call project secrets to upload: a declared secret isn't one of them."""
        return names - set(self.config.secrets)


def prepare_arcade_deploy(
    project_dir: Path, engine_url: str, *, secrets: str, skip_validate: bool
) -> ArcadeDeploy:
    """Read the deploy config and check the project; every refusal happens here.

    Call it once the .env is loaded: declared secrets take their values from the
    environment.
    """
    runners = deployment_runners(engine_url)

    console.print("\nChecking the project...", style="dim")
    config = load_deploy_config(project_dir)
    if config.source:
        console.print(f"✓ Deploy settings from {config.source}", style="green")
    _refuse_mcp_only_settings(config)
    for warning in check_project(project_dir, protocol="arcade", runners=runners):
        console.print(f"[!] {warning}", style="yellow", markup=False)
    warn_about_missing_wheels(project_dir, "arcade", runners)

    values = None
    if config.source:
        refuse_skipping_declared_secrets(config, secrets)
        values = resolve_declared_values(config, os.environ)
        if values.secrets:
            names = ", ".join(sorted(values.secrets))
            console.print(f"✓ Sending {len(values.secrets)} secret(s): {names}", style="green")

    python = None if skip_validate else project_python(project_dir)
    return ArcadeDeploy(config=config, values=values, python=python)


def _refuse_mcp_only_settings(config: DeployConfig) -> None:
    present = [name for name in _MCP_ONLY_SETTINGS if getattr(config, name) is not None]
    if present:
        raise DeployRefusedError(
            f"{', '.join(present)} in the deploy settings ({config.source}) apply only to MCP "
            "servers. This project depends on arcade-mcp, so it deploys as an Arcade server: "
            "it starts from --entrypoint and Arcade calls it through the Arcade worker API. "
            "Remove them; environment and secrets still apply."
        )
