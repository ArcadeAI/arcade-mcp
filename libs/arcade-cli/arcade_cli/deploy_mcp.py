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
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from arcade_cli.console import console
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
    server_already_exists,
    update_deployment,
    watch_rollout,
)
from arcade_cli.deploy_checks import check_project, install_source
from arcade_cli.deploy_config import (
    DeclaredValues,
    load_deploy_config,
    resolve_declared_values,
    runner_settings_json,
)
from arcade_cli.start_command import (
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
) -> None:
    """Deploy the MCP server in ``project_dir``; every refusal happens before the upload."""
    console.print("\nChecking the Arcade Engine can host MCP servers...", style="dim")
    runners = check_mcp_deployments(engine_url)
    console.print("✓ The Engine hosts MCP servers", style="green")

    console.print("\nChecking the project...", style="dim")
    config = load_deploy_config(project_dir)
    if config.source:
        console.print(f"✓ Deploy settings from {config.source}", style="green")
    for warning in check_project(project_dir, protocol="mcp", runners=runners):
        console.print(f"[!] {warning}", style="yellow", markup=False)
    values = resolve_declared_values(config, os.environ)
    if secrets != "auto":
        console.print(
            f"[!] --secrets {secrets} doesn't apply to MCP servers yet: the secrets declared "
            "in the deploy settings are sent.",
            style="yellow",
            markup=False,
        )
    if values.secrets:
        names = ", ".join(sorted(values.secrets))
        console.print(f"✓ Sending {len(values.secrets)} secret(s): {names}", style="green")

    start = resolve_start_command(project_dir, command=config.command, path=config.path)
    console.print(f"✓ Start command: {start.command}", style="green", markup=False)

    if skip_validate:
        _refuse_own_sign_in_by_imports(project_dir)
        if server_name is None or server_version is None:
            raise ValueError("--server-name and --server-version are required with --skip-validate")
        validated = _Validated(server_name, server_version)
    else:
        console.print("\nStarting the server locally to check it...", style="dim")
        validated = _validate(project_dir, start, values, debug)
    console.print(f"✓ Server: {validated.name} {validated.version}", style="green", markup=False)

    console.print("\nCreating deployment package...", style="dim")
    archive = create_mcp_bundle(project_dir, runner_settings_json(config))
    console.print(f"✓ Package created ({len(archive) * 3 / 4 / 1024:.1f} KB)", style="green")

    is_update = _send(engine_url, validated, archive, start, values, provider, debug)
    watch_rollout(engine_url, validated.name, debug, is_update)


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


# Validation


def _validate(
    project_dir: Path, start: StartCommand, values: DeclaredValues, debug: bool
) -> _Validated:
    python = _project_python(project_dir)
    env = {**values.environment, **values.secrets}
    try:
        with run_locally(start, project_dir, env=env, debug=debug, python=python) as endpoint:
            console.print(f"✓ The server answers MCP at {endpoint.path}", style="green")
            _refuse_own_sign_in(endpoint, project_dir)
            _check_tools(endpoint)
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


def _project_python(project_dir: Path) -> Path:
    """The project's own interpreter: its ``.venv``, else an active virtual environment."""
    candidates = [project_dir / ".venv"]
    if os.environ.get("VIRTUAL_ENV"):
        candidates.append(Path(os.environ["VIRTUAL_ENV"]))
    for venv in candidates:
        for python in (venv / "bin" / "python", venv / "Scripts" / "python.exe"):
            if python.exists():
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


def _check_tools(endpoint: LocalEndpoint) -> None:
    try:
        tools = list_tools(endpoint)
    except TokenRequiredError:
        console.print(
            "✓ The server needs a token to list its tools; they appear once a user authorizes it",
            style="green",
        )
        return
    console.print(f"✓ Found {len(tools)} tool(s)", style="green")


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
