"""``arcade deploy`` for MCP servers: FastMCP, the MCP SDK, or any server that serves MCP over
streamable HTTP.

A project that doesn't depend on arcade-mcp deploys through here. Everything that can refuse
the deploy runs before anything is uploaded: the Engine must host MCP servers, the deploy
config and the project must be deployable, and the server must start locally and answer the
MCP handshake. The bundle then goes up with ``protocol: "mcp"``, the start command, and the
declared environment and secrets, which replace the server's previous set.
"""

from __future__ import annotations

import ast
import json
import os
import re
import secrets as secrets_module
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from packaging.version import InvalidVersion, Version

from arcade_cli.console import console
from arcade_cli.context import DeploymentsRunner
from arcade_cli.deploy import (
    CreateDeploymentRequest,
    DeploymentToolkits,
    DeployRefusedError,
    OAuthClientSettings,
    ToolkitBundle,
    UpdateDeploymentRequest,
    check_mcp_deployments,
    create_mcp_bundle,
    deploy_server_to_engine,
    fetch_oauth_callback_url,
    server_already_exists,
    update_deployment,
    watch_rollout,
)
from arcade_cli.deploy_checks import check_project, install_source
from arcade_cli.deploy_config import (
    ApiKey,
    DeclaredValues,
    DeployConfig,
    load_deploy_config,
    reserved_names,
    resolve_declared_values,
    runner_settings_json,
)
from arcade_cli.deploy_wheels import check_wheels
from arcade_cli.secret import load_env_file
from arcade_cli.start_command import (
    RUNNER_HOST,
    LocalEndpoint,
    StartCommand,
    StartCommandError,
    TokenRequiredError,
    fetch_well_known,
    list_tools,
    load_toml,
    project_modules,
    resolve_start_command,
    run_locally,
)

DESCRIPTION = "MCP server deployed via CLI"

# FastMCP providers that make the server its own OAuth authorization server.
_OWN_SIGN_IN_CLASSES = {
    "OAuthProvider",
    "OAuthProxy",
    "OIDCProxy",
    "AzureProvider",
    "GoogleProvider",
    "GitHubProvider",
}


@dataclass(frozen=True)
class _Validated:
    name: str
    version: str


# The newest major versions of each framework Arcade Deploy is tested with.
_TESTED_MAJORS = {"fastmcp": 4, "mcp": 2}
_FRAMEWORK_LABELS = {"fastmcp": "fastmcp", "mcp": "the MCP SDK (mcp)"}


def deploy_mcp_server(
    project_dir: Path,
    engine_url: str,
    *,
    skip_validate: bool,
    server_name: str | None,
    server_version: str | None,
    secrets: str,
    debug: bool,
    provider: str | None,
    env_file: Path | None = None,
) -> None:
    """Deploy the MCP server in ``project_dir``; every refusal happens before the upload.

    ``env_file`` is the .env already loaded into the environment; ``--secrets all`` sends
    each of its entries.
    """
    console.print("\nChecking the Arcade Engine can host MCP servers...", style="dim")
    runners = check_mcp_deployments(engine_url)
    console.print("✓ The Engine hosts MCP servers", style="green")

    console.print("\nChecking the project...", style="dim")
    config = load_deploy_config(project_dir)
    if config.source:
        console.print(f"✓ Deploy settings from {config.source}", style="green")
    for warning in check_project(project_dir, protocol="mcp", runners=runners):
        console.print(f"[!] {warning}", style="yellow", markup=False)
    _warn_about_missing_wheels(project_dir, runners)
    values = _values_to_send(config, secrets, env_file)
    if values.secrets:
        names = ", ".join(sorted(values.secrets))
        console.print(f"✓ Sending {len(values.secrets)} secret(s): {names}", style="green")

    start = resolve_start_command(project_dir, command=config.command, path=config.path)
    console.print(f"✓ Start command: {start.command}", style="green", markup=False)

    if skip_validate:
        _refuse_own_sign_in_by_imports(project_dir)
        if server_name is None or server_version is None:
            raise ValueError("--server-name and --server-version are required with --skip-validate")
        python = _find_project_python(project_dir)
        if python is not None:
            _warn_untested_frameworks(python)
        validated = _Validated(server_name, server_version)
    else:
        console.print("\nStarting the server locally to check it...", style="dim")
        validated = _validate(project_dir, start, values, config.api_key, debug)
    console.print(f"✓ Server: {validated.name} {validated.version}", style="green", markup=False)
    console.print(
        f"✓ Its tools will be listed under the toolkit {engine_toolkit_name(validated.name)}",
        style="green",
        markup=False,
    )

    console.print("\nCreating deployment package...", style="dim")
    archive = create_mcp_bundle(project_dir, runner_settings_json(config))
    console.print(f"✓ Package created ({len(archive) * 3 / 4 / 1024:.1f} KB)", style="green")

    is_update = _send(engine_url, validated, archive, start, values, provider, debug)
    watch_rollout(engine_url, validated.name, debug, is_update)
    if values.oauth_client:
        _print_oauth_callback_url(engine_url, validated.name)


def _print_oauth_callback_url(engine_url: str, server_name: str) -> None:
    """Print the callback URL to register in the identity provider's OAuth app."""
    callback_url = fetch_oauth_callback_url(engine_url, server_name)
    if callback_url is None:
        console.print(
            "\n[!] The Engine didn't return an OAuth callback URL for this server. It may not "
            "support oauth_client in deploys yet, in which case the client wasn't stored and "
            "users can't sign in to this server through it.",
            style="yellow",
            markup=False,
        )
        return
    console.print(
        "\nOAuth callback URL (register it as a redirect URI in your identity provider's app):",
        style="bold",
    )
    console.print(f"  {callback_url}", markup=False, highlight=False, soft_wrap=True)


def _warn_about_missing_wheels(project_dir: Path, runners: list[DeploymentsRunner]) -> None:
    """Warn, never refuse, about dependencies that would compile on the runner."""
    if not any(runner.language == "python" for runner in runners):
        return
    console.print("\nChecking dependencies have prebuilt wheels for the runner...", style="dim")
    result = check_wheels(project_dir, protocol="mcp", runners=runners)
    for warning in result.warnings:
        console.print(f"[!] {warning}", style="yellow", markup=False)
    for note in result.notes:
        console.print(f"[!] {note}", style="dim", markup=False)
    if not result.warnings and not result.notes:
        console.print("✓ Every dependency has a prebuilt wheel for the runner", style="green")


def deploys_mcp_server(project_dir: Path) -> bool:
    """Whether ``project_dir`` is an MCP server project rather than an Arcade one.

    A project with no dependency file stays on the Arcade path, which reports it as it always
    has. A dependency file that can't be read raises ``ProjectCheckError`` rather than being
    taken for an Arcade project.
    """
    from arcade_cli.deploy_checks import DEPENDENCY_SOURCES, detect_protocol

    if not any((project_dir / name).is_file() for name in DEPENDENCY_SOURCES):
        return False
    return detect_protocol(project_dir) == "mcp"


def engine_toolkit_name(server_name: str) -> str:
    """The toolkit name the Engine gives a deployed MCP server's tools.

    Mirrors the Engine's ``formatServerNameAsPascalCase``: lowercase, drop "mcp" and
    "server", split on anything not a letter or digit, capitalize each word. A name left
    empty becomes "Tools".
    """
    name = server_name.lower().replace("mcp", "").replace("server", "")
    words = [word for word in re.split(r"[^a-z0-9]+", name) if word]
    return "".join(word[0].upper() + word[1:] for word in words) or "Tools"


# Secrets


def _values_to_send(config: DeployConfig, mode: str, env_file: Path | None) -> DeclaredValues:
    """The environment and secrets the deploy sends, for the ``--secrets`` mode.

    A deploy replaces the server's whole set of secrets, so ``skip`` can't keep declared
    secrets in place and is refused when there are any.
    """
    mode = mode.lower()
    if mode == "skip" and config.secrets:
        raise DeployRefusedError(
            "--secrets skip would remove the secrets this server declares "
            f"({', '.join(config.secrets)}): a deploy replaces the server's whole set of "
            "secrets. Deploy with --secrets auto to send them."
        )
    values = resolve_declared_values(config, os.environ)
    if mode != "all":
        return values

    entries = load_env_file(str(env_file)) if env_file is not None else {}
    if env_file is None:
        console.print(
            "[!] --secrets all: no .env file was found, so only the declared secrets are sent.",
            style="yellow",
            markup=False,
        )
    names = [name for name in entries if name not in config.environment]
    reserved = reserved_names(names)
    if reserved:
        raise DeployRefusedError(
            f"--secrets all would send {', '.join(reserved)} from {env_file}, which the "
            "deployment runtime reserves for itself. Remove them from .env, or deploy with "
            "--secrets auto to send only the declared secrets."
        )
    # The environment wins over .env, as it did when .env was loaded.
    from_env_file = {name: os.environ.get(name) or entries[name] for name in names}
    return replace(values, secrets={**from_env_file, **values.secrets})


# Untested framework versions


def framework_warning(versions: Mapping[str, str | None]) -> str | None:
    """A warning when the project's frameworks are newer than tested, or absent.

    ``versions`` maps "fastmcp" and "mcp" to their installed versions, ``None`` when
    not installed.
    """
    installed = {name: version for name, version in versions.items() if version}
    if not installed:
        return (
            "Neither fastmcp nor the MCP SDK (mcp) is installed in the project's environment. "
            "Arcade Deploy is tested with servers built on them; the deploy goes ahead."
        )
    untested = []
    for name, version in sorted(installed.items()):
        try:
            major = Version(version).major
        except InvalidVersion:
            continue
        if name in _TESTED_MAJORS and major > _TESTED_MAJORS[name]:
            untested.append(
                f"{_FRAMEWORK_LABELS[name]} {version} (tested up to {_TESTED_MAJORS[name]}.x)"
            )
    if not untested:
        return None
    return (
        f"Arcade Deploy hasn't been tested with {' or '.join(untested)}; the deploy goes "
        "ahead, but check the server once it's running."
    )


def _warn_untested_frameworks(python: Path) -> None:
    versions = _framework_versions(python)
    if not versions:
        return  # The interpreter couldn't be asked; say nothing rather than guess.
    warning = framework_warning(versions)
    if warning:
        console.print(f"[!] {warning}", style="yellow", markup=False)


_VERSIONS_SCRIPT = """
import importlib.metadata as m, json
versions = {}
for name in ("fastmcp", "mcp"):
    try:
        versions[name] = m.version(name)
    except m.PackageNotFoundError:
        versions[name] = None
print(json.dumps(versions))
"""


def _framework_versions(python: Path) -> dict[str, str | None]:
    """fastmcp's and the MCP SDK's versions as the project's own interpreter sees them."""
    try:
        result = subprocess.run(
            [str(python), "-c", _VERSIONS_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        versions = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}
    if not isinstance(versions, dict):
        return {}
    return {str(k): (str(v) if v else None) for k, v in versions.items()}


# Validation


def _validate(
    project_dir: Path,
    start: StartCommand,
    values: DeclaredValues,
    api_key: ApiKey | None,
    debug: bool,
) -> _Validated:
    python = _project_python(project_dir)
    _warn_untested_frameworks(python)
    key_env, headers = _local_api_key(api_key, values)
    # The runner sets ARCADE_WORKER_SECRET; with it an Arcade server serves /worker/*.
    env = {
        **values.environment,
        **values.secrets,
        **key_env,
        "ARCADE_WORKER_SECRET": secrets_module.token_urlsafe(32),
    }
    try:
        with run_locally(
            start, project_dir, env=env, debug=debug, python=python, headers=headers
        ) as endpoint:
            if (
                api_key is not None
                and endpoint.handshake is None
                and _refuses_key(api_key, endpoint.token_challenge)
            ):
                raise _key_refused(api_key, values)
            console.print(f"✓ The server answers MCP at {endpoint.path}", style="green")
            _refuse_arcade_worker(endpoint)
            _refuse_own_sign_in(endpoint, project_dir)
            _check_tools(endpoint, api_key, values, headers)
            name = endpoint.handshake.server_name if endpoint.handshake else ""
            version = endpoint.handshake.server_version if endpoint.handshake else ""
    except StartCommandError:
        # A server that can't start locally may still run its own sign-in; say that instead.
        _refuse_own_sign_in_by_imports(project_dir)
        raise
    pyproject = _pyproject_project(project_dir)
    return _Validated(
        name=name or str(pyproject.get("name") or project_dir.name),
        version=version or str(pyproject.get("version") or "0.0.0"),
    )


def _find_project_python(project_dir: Path) -> Path | None:
    """The project's own interpreter: its ``.venv``, else an active virtual environment."""
    candidates = [project_dir / ".venv"]
    if os.environ.get("VIRTUAL_ENV"):
        candidates.append(Path(os.environ["VIRTUAL_ENV"]))
    for venv in candidates:
        for python in (venv / "bin" / "python", venv / "Scripts" / "python.exe"):
            if python.exists():
                return python
    return None


def _project_python(project_dir: Path) -> Path:
    """The project's own interpreter; refuses the deploy when it has none."""
    python = _find_project_python(project_dir)
    if python is not None:
        return python
    setup = {
        "uv.lock": "uv sync",
        "requirements.txt": "uv venv && uv pip install -r requirements.txt",
        "pyproject.toml": "uv venv && uv pip install -r pyproject.toml",
    }.get(str(install_source(project_dir, "mcp")), "uv venv, then install its dependencies")
    raise DeployRefusedError(
        "This project has no virtual environment to run the server in, so it can't be checked "
        f"before deploying. Create one in the project (`{setup}`) and deploy again, or skip the "
        "check with --skip-validate --server-name NAME --server-version VERSION."
    )


def _check_tools(
    endpoint: LocalEndpoint,
    api_key: ApiKey | None,
    values: DeclaredValues,
    headers: Mapping[str, str],
) -> None:
    try:
        tools = list_tools(endpoint, headers=headers)
    except TokenRequiredError as needs_token:
        if api_key is not None and _refuses_key(api_key, needs_token.challenge):
            raise _key_refused(api_key, values) from None
        console.print(
            "✓ The server needs a token to list its tools; they appear once a user authorizes it",
            style="green",
        )
        return
    console.print(f"✓ Found {len(tools)} tool(s)", style="green")


# API keys


def _local_api_key(
    api_key: ApiKey | None, values: DeclaredValues
) -> tuple[dict[str, str], dict[str, str]]:
    """The key's environment variable and request header for the local check.

    The key is the declared secret's value when ``api_key.env`` names one, else a random
    key, as the runner generates.
    """
    if api_key is None:
        return {}, {}
    key = values.secrets.get(api_key.env) or secrets_module.token_urlsafe(32)
    value = f"{api_key.scheme} {key}" if api_key.scheme else key
    return {api_key.env: key}, {api_key.header: value}


def _refuses_key(api_key: ApiKey, challenge: str | None) -> bool:
    """Whether a 401/403 sent with the key means the key was refused.

    A Bearer challenge asks for a user's OAuth token. When the key travels in another
    header the server took it, and the tools appear once a user authorizes, as for any
    server behind OAuth. When the key itself goes in Authorization, the challenge is the
    key being refused.
    """
    if not (challenge or "").lower().startswith("bearer"):
        return True
    return api_key.header.lower() == "authorization"


def _key_refused(api_key: ApiKey, values: DeclaredValues) -> DeployRefusedError:
    if api_key.env in values.secrets:
        return DeployRefusedError(
            f"The server refused the API key from the secret {api_key.env} (api_key.env), sent "
            f"in the {api_key.header} header. Check {api_key.env} holds the key the server "
            "expects, and that api_key.header and api_key.scheme match how it reads it."
        )
    return DeployRefusedError(
        f"The server refused a generated API key put in {api_key.env} (api_key.env) and sent in "
        f"the {api_key.header} header, so it doesn't read its key from {api_key.env}. If it "
        f"checks a fixed key, declare {api_key.env} under `secrets` holding that key."
    )


# Arcade servers


def _refuse_arcade_worker(endpoint: LocalEndpoint) -> None:
    """Refuse an Arcade server: it answers the Arcade worker API's health check."""
    try:
        response = httpx.get(f"http://{RUNNER_HOST}:{endpoint.port}/worker/health", timeout=5.0)
    except httpx.HTTPError:
        return
    if response.status_code == 200:
        raise DeployRefusedError(
            "This server answers the Arcade worker API (GET /worker/health), so it's an "
            "Arcade server, but the project doesn't list arcade-mcp among its dependencies. "
            "Add arcade-mcp (or arcade-mcp-server) to its dependencies and deploy again."
        )


# Servers that run their own sign-in


def _refuse_own_sign_in(endpoint: LocalEndpoint, project_dir: Path) -> None:
    """Refuse a server that is its own OAuth authorization server.

    FastMCP serves authorization server metadata only from an ``OAuthProvider``: the base of
    ``OAuthProxy`` and ``OIDCProxy``. Its issuer may sit under a path, so the paths the
    server's protected resource metadata names are checked too.
    """
    resource = fetch_well_known(endpoint, "oauth-protected-resource") or {}
    issuer_paths = [
        urlparse(str(server)).path
        for server in resource.get("authorization_servers") or []
        if urlparse(str(server)).path not in ("", "/")
    ]
    if fetch_well_known(endpoint, "oauth-authorization-server", paths=issuer_paths):
        raise _own_sign_in_refusal(_own_sign_in_classes(project_dir))


def _refuse_own_sign_in_by_imports(project_dir: Path) -> None:
    found = _own_sign_in_classes(project_dir)
    if found:
        raise _own_sign_in_refusal(found)


def _own_sign_in_refusal(classes: list[str]) -> DeployRefusedError:
    which = f" ({', '.join(classes)})" if classes else ""
    return DeployRefusedError(
        f"This server runs its own OAuth authorization server{which}, which Arcade Deploy "
        "doesn't host yet. Verify tokens from your identity provider instead "
        "(RemoteAuthProvider or JWTVerifier), or host the server elsewhere and add it to "
        "Arcade as a remote MCP server."
    )


def _own_sign_in_classes(project_dir: Path) -> list[str]:
    """fastmcp sign-in providers the project imports."""
    found: set[str] = set()
    for _, tree in project_modules(project_dir):
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("fastmcp"):
                found.update(a.name for a in node.names if a.name in _OWN_SIGN_IN_CLASSES)
    return sorted(found)


# Upload


def _send(
    engine_url: str,
    validated: _Validated,
    archive: str,
    start: StartCommand,
    values: DeclaredValues,
    provider: str | None,
    debug: bool,
) -> bool:
    """Create or update the deployment; whether it was an update."""
    toolkits = DeploymentToolkits(
        bundles=[
            ToolkitBundle.mcp_server(validated.name, validated.version, archive, start.command)
        ]
    )
    oauth_client = OAuthClientSettings(**values.oauth_client) if values.oauth_client else None
    try:
        if server_already_exists(engine_url, validated.name):
            update = UpdateDeploymentRequest(
                description=DESCRIPTION,
                toolkits=toolkits,
                environment=values.environment,
                secrets=values.secrets,
                oauth_client=oauth_client,
            )
            update_deployment(engine_url, validated.name, update.model_dump(), debug)
            return True
        create = CreateDeploymentRequest(
            name=validated.name,
            description=DESCRIPTION,
            toolkits=toolkits,
            provider=provider,
            environment=values.environment,
            secrets=values.secrets,
            oauth_client=oauth_client,
        )
        deploy_server_to_engine(engine_url, create.model_dump(), debug)
    except Exception as e:
        raise ValueError(f"Deployment failed: {e}") from e
    return False


def _pyproject_project(project_dir: Path) -> dict[str, Any]:
    path = project_dir / "pyproject.toml"
    try:
        project = load_toml(path).get("project") if path.is_file() else None
    except Exception:
        return {}
    return project if isinstance(project, dict) else {}
