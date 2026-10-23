"""The deploy config of an MCP server deploy.

Read from ``[tool.arcade.deploy]`` in pyproject.toml, else from ``[deploy]`` in an
``arcade.toml`` beside the server, for projects with only a requirements.txt. Most servers
need none: the start command, port and path are detected.

The CLI is the only parser of this config. It sends the start command, environment,
secrets and OAuth client in the deploy request, and writes the runner's share
(``api_key``, ``path``) to ``.arcade/deploy.json`` in the bundle, so the runner never reads
the author's files.

Settings hold names and formats only, never a credential value: a secret is named here
and its value read from the deployer's environment or .env at deploy time.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from arcade_cli.start_command import load_toml

RUNNER_SETTINGS_PATH = ".arcade/deploy.json"

# The runner sets these for itself and refuses a deployment that declares one. The
# ARCADE_BUNDLE_* and ARCADE_ARTIFACT_STORE_URL names are older names it still reads.
_RESERVED_PREFIXES = ("ARCADE_RUNNER_", "KUBERNETES_", "ARCADE_TELEMETRY_")
_RESERVED_NAMES = frozenset({
    "ARCADE_WORKER_SECRET",
    "ARCADE_ARTIFACT_STORE_URL",
    "ARCADE_BUNDLE_URL",
    "ARCADE_BUNDLE_KEY",
    "ARCADE_BUNDLE_DIR",
    "ARCADE_BUNDLE_NAME",
    "ARCADE_BUNDLE_ENTRYPOINT",
    "WORKER_PORT",
    "WORKER_PACKAGES",
    "WORKER_CACHE_ENABLED",
    "WORKER_CACHE_BUCKET",
    "WORKER_BUNDLE_BUCKET",
    "WORKER_BUNDLE_PATHS",
    "WORKER_API_CONFIG_ENABLED",
    "PATH",
    "HOME",
    "TMPDIR",
    "FASTMCP_HOME",
    "UV_PROJECT_ENVIRONMENT",
    "UV_CACHE_DIR",
    "UV_PYTHON_DOWNLOADS",
    "PIP_CACHE_DIR",
})

# The platform credential's header: the runner strips it from every request.
_PLATFORM_CREDENTIAL_HEADER = "Arcade-Worker-Auth"

_VARIABLE_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


class DeployConfigError(ValueError):
    """The deploy config can't be read or is refused; nothing is uploaded."""


class ApiKey(BaseModel):
    """Where a server that checks a static key expects it."""

    model_config = ConfigDict(extra="forbid")

    env: str
    header: str
    scheme: str | None = None


class OAuthClient(BaseModel):
    """A pre-registered OAuth client, for identity providers without dynamic registration."""

    model_config = ConfigDict(extra="forbid")

    client_id: str
    client_secret_env: str


class DeployConfig(BaseModel):
    """The settings of ``[tool.arcade.deploy]`` or an ``arcade.toml``'s ``[deploy]``."""

    model_config = ConfigDict(extra="forbid")

    command: str | None = None
    environment: dict[str, str] = Field(default_factory=dict)
    secrets: list[str] = Field(default_factory=list)
    api_key: ApiKey | None = None
    oauth_client: OAuthClient | None = None
    path: str | None = None

    _source: Literal["pyproject.toml", "arcade.toml"] | None = PrivateAttr(default=None)

    @property
    def source(self) -> Literal["pyproject.toml", "arcade.toml"] | None:
        """The file the settings came from, or ``None`` when the project has none."""
        return self._source

    @model_validator(mode="after")
    def _check(self) -> DeployConfig:
        if self.command is not None and not self.command.strip():
            raise ValueError("`command` is empty. Set it to the command that starts your server.")
        if self.path is not None and not self.path.startswith("/"):
            raise ValueError(f"`path` must start with '/': {self.path!r}")
        if self.api_key and self.api_key.header.lower() == _PLATFORM_CREDENTIAL_HEADER.lower():
            raise ValueError(
                f"`api_key.header` can't be {_PLATFORM_CREDENTIAL_HEADER}: Arcade uses that header "
                "to authenticate its own calls to the server."
            )
        _check_names(self)
        return self


def _check_names(config: DeployConfig) -> None:
    # Names set in the server's environment, and every name the config refers to.
    deployed = [*config.environment, *config.secrets]
    if config.api_key:
        deployed.append(config.api_key.env)
    named = deployed + ([config.oauth_client.client_secret_env] if config.oauth_client else [])

    for name in named:
        if not _VARIABLE_NAME.match(name):
            raise ValueError(f"{name!r} isn't a valid environment variable name.")
    for name in deployed:
        if name in _RESERVED_NAMES or name.startswith(_RESERVED_PREFIXES):
            raise ValueError(
                f"{name} is reserved for the deployment runtime; declare the value under "
                "another name."
            )
    both = sorted(set(config.environment) & set(config.secrets))
    if both:
        raise ValueError(f"Declared as both an environment value and a secret: {', '.join(both)}")


def load_deploy_config(project_dir: Path) -> DeployConfig:
    """Read the project's deploy config; an empty one when it has none."""
    table: Any = {}
    source: Literal["pyproject.toml", "arcade.toml"] | None = None

    pyproject = project_dir / "pyproject.toml"
    if pyproject.is_file():
        deploy = _table(_read_toml(pyproject), ("tool", "arcade", "deploy"), pyproject.name)
        if deploy is not None:
            table, source = deploy, "pyproject.toml"

    arcade_toml = project_dir / "arcade.toml"
    if arcade_toml.is_file():
        deploy = _table(_read_toml(arcade_toml), ("deploy",), arcade_toml.name)
        if deploy is not None and source == "pyproject.toml":
            raise DeployConfigError(
                "This project has deploy settings in both [tool.arcade.deploy] in "
                "pyproject.toml and [deploy] in arcade.toml. Keep one of them."
            )
        if deploy is not None:
            table, source = deploy, "arcade.toml"

    where = f"[tool.arcade.deploy] in {source}" if source == "pyproject.toml" else str(source)
    try:
        config = DeployConfig.model_validate(table)
    except ValidationError as e:
        problems = "\n".join(f"  {_describe(error)}" for error in e.errors())
        raise DeployConfigError(f"The deploy settings in {where} are invalid:\n{problems}") from e
    config._source = source
    return config


def _table(data: dict[str, Any], keys: tuple[str, ...], file_name: str) -> Any:
    """The value at ``keys`` in a TOML document, or ``None`` when it's absent.

    Every enclosing key must be a table; the value itself is validated by the caller.
    """
    value: Any = data
    for depth, key in enumerate(keys):
        if not isinstance(value, dict):
            enclosing = ".".join(keys[:depth])
            raise DeployConfigError(f"{file_name}: [{enclosing}] isn't a table.")
        value = value.get(key)
        if value is None:
            return None
    return value


def _describe(error: Any) -> str:
    location = ".".join(str(part) for part in error["loc"])
    if error["type"] == "extra_forbidden":
        nested: dict[str, type[BaseModel]] = {"api_key": ApiKey, "oauth_client": OAuthClient}
        owner = (
            nested.get(str(error["loc"][0]), DeployConfig)
            if len(error["loc"]) > 1
            else DeployConfig
        )
        known = ", ".join(owner.model_fields)
        return f"{location} isn't a deploy setting (the settings are {known})"
    message = str(error["msg"]).removeprefix("Value error, ")
    return f"{location}: {message}" if location else message


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        return load_toml(path)
    except Exception as e:
        raise DeployConfigError(f"{path.name} couldn't be read: {e}") from e


@dataclass(frozen=True)
class DeclaredValues:
    """What an MCP server deploy sends: values for every declared name."""

    environment: dict[str, str]
    secrets: dict[str, str]
    oauth_client: dict[str, str] | None


def resolve_declared_values(config: DeployConfig, env: Mapping[str, str]) -> DeclaredValues:
    """Fill the declared secrets and OAuth client secret from the deployer's environment."""
    missing = [name for name in config.secrets if not env.get(name)]
    if missing:
        raise DeployConfigError(
            "Declared secrets have no value in your environment or .env: " + ", ".join(missing)
        )

    oauth_client = None
    if config.oauth_client:
        secret_name = config.oauth_client.client_secret_env
        client_secret = env.get(secret_name)
        if not client_secret:
            raise DeployConfigError(
                f"oauth_client.client_secret_env names {secret_name}, which has no value in "
                "your environment or .env."
            )
        oauth_client = {"client_id": config.oauth_client.client_id, "client_secret": client_secret}

    return DeclaredValues(
        environment=dict(config.environment),
        secrets={name: env[name] for name in config.secrets},
        oauth_client=oauth_client,
    )


def runner_settings_json(config: DeployConfig) -> str | None:
    """The contents of ``.arcade/deploy.json``, or ``None`` when the runner needs nothing."""
    settings: dict[str, Any] = {}
    if config.api_key:
        settings["api_key"] = config.api_key.model_dump(exclude_none=True)
    if config.path:
        settings["path"] = config.path
    return json.dumps(settings, indent=2) + "\n" if settings else None
