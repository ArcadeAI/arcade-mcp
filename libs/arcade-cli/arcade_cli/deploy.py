import asyncio
import base64
import io
import os
import random
import subprocess
import tarfile
import time
from collections import deque
from pathlib import Path
from typing import cast

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.prompt import Confirm
from rich.spinner import Spinner
from rich.text import Text
from typing_extensions import Literal

from arcade_cli.configure import find_python_interpreter
from arcade_cli.secret import load_env_file
from arcade_cli.utils import (
    compute_base_url,
    get_auth_headers,
    get_org_scoped_url,
    validate_and_get_config,
)

console = Console()

# Models


class MCPClientInfo(BaseModel):
    """MCP client information for initialize request."""

    name: str
    version: str


class MCPInitializeParams(BaseModel):
    """Parameters for MCP initialize request."""

    capabilities: dict = Field(default_factory=dict)
    clientInfo: MCPClientInfo
    protocolVersion: str


class MCPInitializeRequest(BaseModel):
    """MCP initialize request payload."""

    id: int
    jsonrpc: str = "2.0"
    method: str = "initialize"
    params: MCPInitializeParams


class ToolkitBundle(BaseModel):
    """A toolkit bundle for deployment."""

    name: str
    version: str
    bytes: str
    type: str = "mcp"
    entrypoint: str


class DeploymentToolkits(BaseModel):
    """Toolkits section of deployment request."""

    bundles: list[ToolkitBundle]
    packages: list[str] = Field(default_factory=list)


class CreateDeploymentRequest(BaseModel):
    """Deployment request payload for /v1/deployments endpoint."""

    name: str
    description: str
    toolkits: DeploymentToolkits


class UpdateDeploymentRequest(BaseModel):
    """Deployment request payload for /v1/deployments/{deployment_name} endpoint."""

    description: str
    toolkits: DeploymentToolkits


# Deployment Status Functions


def _get_deployment_status(engine_url: str, server_name: str) -> str:
    """
    Get the status of a deployment.

    Args:
        engine_url: The base URL of the Arcade Engine
        server_name: The name of the server to get the status of

    Returns:
        The status of the deployment.
        Possible values are: "pending", "updating", "unknown", "running", "failed".
    """
    url = get_org_scoped_url(engine_url, f"/deployments/{server_name}/status")
    client = httpx.Client(headers=get_auth_headers(), timeout=360)
    response = client.get(url)
    response.raise_for_status()
    status = cast(str, response.json().get("status", "unknown"))
    return status


async def _poll_deployment_status(
    engine_url: str,
    server_name: str,
    state: dict,
    debug: bool = False,
) -> None:
    """Poll deployment status until it's running or error."""
    while state["status"] in ["pending", "unknown", "updating"]:
        try:
            status = _get_deployment_status(engine_url, server_name)
            state["status"] = status
            if status in ["running", "failed"]:
                break
        except Exception as e:
            if debug:
                console.print(f"Error polling status: {e}", style="dim red")
        await asyncio.sleep(5)


async def _stream_deployment_logs_to_deque(
    engine_url: str,
    server_name: str,
    log_deque: deque,
    state: dict,
    debug: bool = False,
) -> None:
    """Stream deployment logs into a deque with retry logic."""
    stream_url = get_org_scoped_url(engine_url, f"/deployments/{server_name}/logs/stream")

    while state["status"] in ["pending", "unknown", "updating"]:
        try:
            auth_headers = get_auth_headers()
            async with (
                httpx.AsyncClient(timeout=None) as client,  # noqa: S113 - expected indefinite log stream
                client.stream("GET", stream_url, headers=auth_headers) as response,
            ):
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        log_deque.append(line)
                    # End state check
                    if state["status"] not in ["pending", "unknown", "updating"]:
                        break
        except httpx.HTTPStatusError as e:
            if debug:
                console.print(f"Failed to stream logs: {e.response.status_code}", style="dim red")
            await asyncio.sleep(3)
        except Exception as e:
            if debug:
                console.print(f"Error streaming logs: {e}", style="dim red")
            await asyncio.sleep(3)


async def _monitor_deployment_with_logs(
    engine_url: str,
    server_name: str,
    debug: bool = False,
    is_update: bool = False,
) -> tuple[Literal["running", "failed"], list[str]]:
    """
    Monitor deployment with live status and streaming logs display.

    Args:
        engine_url: The base URL of the Arcade Engine
        server_name: The name of the server to monitor
        debug: Whether to show debug information
        is_update: If True, wait for status to be 'updating' before streaming logs or 'failed' before exiting

    Returns:
        Tuple of (final status, list of all logs collected)
    """
    state = {"status": "pending"}
    log_deque: deque[str] = deque(maxlen=1000)

    # Friendly messages that rotate while waiting for logs
    waiting_messages = [
        "Waiting for logs...",
        "Still getting logs ready...",
        "Build environment warming up...",
        "Preparing deployment resources...",
    ]

    status_task = asyncio.create_task(
        _poll_deployment_status(engine_url, server_name, state, debug)
    )

    # Don't stream logs until the deployment is 'updating' or 'failed' otherwise we will get logs from the previous deployment
    if is_update:
        while state["status"] not in ["updating", "failed"]:
            await asyncio.sleep(1)

    # Start log streaming task
    logs_task = asyncio.create_task(
        _stream_deployment_logs_to_deque(engine_url, server_name, log_deque, state, debug)
    )

    # Live display with spinner and logs
    spinner = Spinner("dots", style="green")
    log_spinner = Spinner("dots", style="dim")

    start_time = time.time()

    with Live(console=console, refresh_per_second=4) as live:
        while state["status"] in ["pending", "unknown", "updating"]:
            elapsed = int(time.time() - start_time)

            # Show different messages based on status
            if state["status"] == "updating":
                status_text = Text(
                    "Updating deployment (this may take a few minutes)...", style="bold green"
                )
            else:
                status_text = Text(
                    "Deployment in progress (this may take a few minutes)...", style="bold green"
                )
            status_line = Columns([spinner, status_text], padding=(0, 1))

            logs_header = Text("\nRecent logs:", style="dim")

            if log_deque:
                # Get the last logs and ensure we only show 6 lines total
                recent_logs = list(log_deque)[-6:]
                log_lines_text = Text()
                for log_line in recent_logs:
                    log_lines_text.append(f"  {log_line}\n", style="dim")
                # Pad with empty lines if we have fewer than 6 logs
                for _ in range(6 - len(recent_logs)):
                    log_lines_text.append("\n")

                footer = Text(
                    "\nYou can safely exit with Ctrl+C at any time. The deployment will continue normally.",
                    style="green",
                )
                display = Group(Text("\n"), status_line, logs_header, log_lines_text, footer)
            else:
                # Rotate message every 7 seconds while waiting for logs
                message_index = (elapsed // 7) % len(waiting_messages)
                current_message = waiting_messages[message_index]
                waiting_line = Columns(
                    [log_spinner, Text(current_message, style="dim italic")], padding=(0, 1)
                )
                padding = Text("\n" * 5)
                footer = Text(
                    "\nYou can safely exit with Ctrl+C at any time. The deployment will continue normally.",
                    style="green",
                )
                display = Group(
                    Text("\n"), status_line, logs_header, Text("  "), waiting_line, padding, footer
                )

            live.update(display)
            await asyncio.sleep(0.25)

    status_task.cancel()
    logs_task.cancel()
    await asyncio.gather(status_task, logs_task, return_exceptions=True)

    all_logs = list(log_deque)

    return cast(Literal["running", "failed"], state["status"]), all_logs


# Create Deployment Functions


def server_already_exists(engine_url: str, server_name: str) -> bool:
    """Check if a server already exists in the Arcade Engine."""
    url = get_org_scoped_url(engine_url, f"/workers/{server_name}")
    client = httpx.Client(headers=get_auth_headers())
    response = client.get(url)
    if response.status_code == 404:
        return False

    response.raise_for_status()

    return cast(bool, response.json().get("managed"))


def update_deployment(
    engine_url: str,
    server_name: str,
    update_deployment_request: dict,
) -> None:
    """Update a deployment in the Arcade Engine."""
    url = get_org_scoped_url(engine_url, f"/deployments/{server_name}")
    client = httpx.Client(headers=get_auth_headers())
    response = client.put(url, json=update_deployment_request)
    response.raise_for_status()


def create_package_archive(package_dir: Path) -> str:
    """
    Create a tar.gz archive of the package directory.

    Args:
        package_dir: Path to the package directory to archive

    Returns:
        Base64-encoded string of the tar.gz archive bytes

    Raises:
        ValueError: If package_dir doesn't exist or is not a directory
    """
    if not package_dir.exists():
        raise ValueError(f"Package directory not found: {package_dir}")

    if not package_dir.is_dir():
        raise ValueError(f"Package path must be a directory: {package_dir}")

    def exclude_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        """Filter for files/directories to exclude from the archive.

        Filters out:
        - Hidden files and directories
        - __pycache__ directories
        - .egg-info directories
        - dist and build directories
        - files ending with .lock
        """
        name = tarinfo.name

        parts = Path(name).parts

        for part in parts:
            if (
                part.startswith(".")
                or part == "__pycache__"
                or part.endswith(".egg-info")
                or part in ["dist", "build"]
                or part.endswith(".lock")
            ):
                return None

        return tarinfo

    # Create tar.gz archive in memory
    byte_stream = io.BytesIO()
    with tarfile.open(fileobj=byte_stream, mode="w:gz") as tar:
        tar.add(package_dir, arcname=package_dir.name, filter=exclude_filter)

    # Get bytes and encode to base64
    byte_stream.seek(0)
    package_bytes = byte_stream.read()
    package_bytes_b64 = base64.b64encode(package_bytes).decode("utf-8")

    return package_bytes_b64


def start_server_process(entrypoint: str, debug: bool = False) -> tuple[subprocess.Popen, int]:
    """
    Start the MCP server process on a random port.

    Args:
        entrypoint: Path to the entrypoint file that runs the MCPApp instance
        debug: Whether to show debug information

    Returns:
        Tuple of (process, port)

    Raises:
        ValueError: If the server process exits immediately
    """
    port = random.randint(8000, 9000)  # noqa: S311

    # override MCPApp.run() settings
    env = {
        **os.environ,
        "ARCADE_SERVER_HOST": "localhost",
        "ARCADE_SERVER_PORT": str(port),
        "ARCADE_SERVER_TRANSPORT": "http",
        "ARCADE_AUTH_DISABLED": "true",
        "ARCADE_WORKER_SECRET": "temp-validation-secret",
    }

    # Use the project's Python environment, not the CLI's isolated environment.
    # find_python_interpreter() looks for .venv/bin/python in cwd, falling back to sys.executable.
    # This ensures the server runs in the project's environment even when the CLI is installed
    # in an isolated environment (e.g., via 'uv tool install arcade-mcp').
    project_python = find_python_interpreter()
    cmd = [str(project_python), entrypoint]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    # Check for immediate failure on start up
    time.sleep(0.5)
    if process.poll() is not None:
        _, stderr = process.communicate()
        error_msg = stderr.strip() if stderr else "Unknown error"
        raise ValueError(f"Server process exited immediately: {error_msg}")

    return process, port


def wait_for_health(base_url: str, process: subprocess.Popen, timeout: int = 30) -> None:
    """
    Wait for the server to become healthy.

    Args:
        base_url: Base URL of the server
        process: The server process
        timeout: Maximum time to wait in seconds

    Raises:
        ValueError: If the server doesn't become healthy within timeout
    """
    health_url = f"{base_url}/worker/health"
    start_time = time.time()
    is_healthy = False

    while time.time() - start_time < timeout:
        try:
            response = httpx.get(health_url, timeout=2.0)
            if response.status_code == 200:
                is_healthy = True
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        except Exception:
            console.print("  Health check failed. Trying again...", style="dim")
        time.sleep(0.5)

    if not is_healthy:
        process.terminate()
        try:
            _, stderr = process.communicate(timeout=2)
            error_msg = stderr.strip() if stderr else "Server failed to become healthy"
        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = f"Server failed to become healthy within {timeout} seconds"
        raise ValueError(error_msg)

    console.print("✓ Server is healthy", style="green")


def get_server_info(base_url: str) -> tuple[str, str]:
    """
    Extract server name and version via the MCP initialize endpoint.

    Args:
        base_url: Base URL of the server

    Returns:
        Tuple of (server_name, server_version)

    Raises:
        ValueError: If server info extraction fails
    """
    mcp_url = f"{base_url}/mcp"

    initialize_request = MCPInitializeRequest(
        id=1,
        params=MCPInitializeParams(
            clientInfo=MCPClientInfo(name="arcade-deploy-client", version="1.0.0"),
            protocolVersion="2025-06-18",
        ),
    )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        mcp_response = httpx.post(
            mcp_url, json=initialize_request.model_dump(), headers=headers, timeout=10.0
        )
        mcp_response.raise_for_status()
        mcp_data = mcp_response.json()

        server_name = mcp_data["result"]["serverInfo"]["name"]
        server_version = mcp_data["result"]["serverInfo"]["version"]

        console.print(f"✓ Found server name: {server_name}", style="green")
        console.print(f"✓ Found server version: {server_version}", style="green")

    except Exception as e:
        raise ValueError(f"Failed to extract server info from /mcp endpoint: {e}") from e
    else:
        return server_name, server_version


def get_required_secrets(
    base_url: str, server_name: str, server_version: str, debug: bool = False
) -> set[str]:
    """
    Extract required secrets from the /worker/tools endpoint.

    Args:
        base_url: Base URL of the server
        server_name: Name of the server (for display purposes)
        server_version: Version of the server (for display purposes)
        debug: Whether to show debug information

    Returns:
        Set of required secret keys

    Raises:
        ValueError: If secrets extraction fails
    """
    tools_url = f"{base_url}/worker/tools"

    try:
        tools_response = httpx.get(tools_url, timeout=10.0)
        tools_response.raise_for_status()
        tools_data = tools_response.json()

        required_secrets = set()
        for tool in tools_data:
            if (
                "requirements" in tool
                and tool["requirements"]
                and "secrets" in tool["requirements"]
                and tool["requirements"]["secrets"]
            ):
                for secret in tool["requirements"]["secrets"]:
                    if secret.get("key"):
                        required_secrets.add(secret["key"])

        console.print(f"✓ Found {len(tools_data)} tools", style="green")

    except Exception as e:
        raise ValueError(f"Failed to extract tool secrets from /worker/tools endpoint: {e}") from e
    else:
        return required_secrets


def verify_server_and_get_metadata(
    entrypoint: str, debug: bool = False
) -> tuple[str, str, set[str]]:
    """
    Start the server, verify it's healthy, and extract metadata.

    This function orchestrates:
    1. Starting the server on a random port
    2. Waiting for the server to become healthy
    3. Extracting server name and version via POST /mcp (initialize method)
    4. Extracting required secrets via GET /worker/tools
    5. Stopping the server
    6. Returning the metadata

    Args:
        entrypoint: Path to the entrypoint file that runs the MCPApp instance
        debug: Whether to show debug information

    Returns:
        Tuple of (server_name, server_version, required_secrets_set)

    Raises:
        ValueError: If the server fails to start or metadata extraction fails
    """
    process, port = start_server_process(entrypoint, debug)
    console.print(f"✓ Server started on port {port}", style="green")
    base_url = f"http://127.0.0.1:{port}"

    try:
        wait_for_health(base_url, process)

        server_name, server_version = get_server_info(base_url)

        required_secrets = get_required_secrets(base_url, server_name, server_version, debug)
        console.print(f"✓ Found {len(required_secrets)} required secret(s)", style="green")

        return server_name, server_version, required_secrets

    finally:
        # Always stop the server
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        if debug:
            console.print("✓ Server stopped", style="green")


def upsert_secrets_to_engine(
    engine_url: str,
    secrets: set[str],
    debug: bool = False,
) -> None:
    """
    Upsert secrets to the Arcade Engine.

    Args:
        engine_url: The base URL of the Arcade Engine
        secrets: Set of secret keys to upsert
        debug: Whether to show debug information
    """
    if not secrets:
        return

    client = httpx.Client(headers=get_auth_headers())

    for secret_key in sorted(secrets):
        secret_value = os.getenv(secret_key)

        if secret_value:
            console.print(
                f"✓ Uploading '{secret_key}' with value ending in ...{secret_value[-4:]}",
                style="green",
            )
        else:
            console.print(
                f"⚠️  Secret '{secret_key}' not found in environment, skipping upload.",
                style="yellow",
            )
            continue

        try:
            # Upsert secret to engine
            url = get_org_scoped_url(engine_url, f"/secrets/{secret_key}")
            response = client.put(
                url,
                json={"description": "Secret set via CLI", "value": secret_value},
                timeout=30,
            )
            response.raise_for_status()
            console.print(f"✓ Secret '{secret_key}' uploaded", style="green")
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to upload secret '{secret_key}': HTTP {e.response.status_code}"
            if debug:
                console.print(f"❌ {error_msg}: {e.response.text}", style="red")
            else:
                console.print(f"❌ {error_msg}", style="red")
        except Exception as e:
            error_msg = f"Failed to upload secret '{secret_key}': {e}"
            console.print(f"❌ {error_msg}", style="red")

    client.close()


def deploy_server_to_engine(
    engine_url: str,
    deployment_request: dict,
    debug: bool = False,
) -> dict:
    """
    Deploy the server to Arcade Engine.

    Args:
        engine_url: The base URL of the Arcade Engine
        deployment_request: The deployment request payload
        debug: Whether to show debug information

    Returns:
        The response JSON from the deployment API

    Raises:
        httpx.HTTPStatusError: If the deployment request fails
        httpx.ConnectError: If connection to the engine fails
    """
    url = get_org_scoped_url(engine_url, "/deployments")
    client = httpx.Client(headers=get_auth_headers(), timeout=360)

    try:
        response = client.post(url, json=deployment_request)
        response.raise_for_status()
        return cast(dict, response.json())
    except httpx.ConnectError as e:
        raise ValueError(f"Failed to connect to Arcade Engine at {engine_url}: {e}") from e
    except httpx.HTTPStatusError as e:
        error_detail = ""
        try:
            error_json = e.response.json()
            error_detail = f": {error_json}"
        except Exception:
            error_detail = f": {e.response.text}"

        raise ValueError(
            f"Deployment failed with HTTP {e.response.status_code}{error_detail}"
        ) from e
    finally:
        client.close()


def deploy_server_logic(
    entrypoint: str,
    skip_validate: bool,
    server_name: str | None,
    server_version: str | None,
    secrets: str,
    host: str,
    port: int | None,
    force_tls: bool,
    force_no_tls: bool,
    debug: bool,
) -> None:
    """
    Main logic for deploying an MCP server to Arcade Engine.

    Args:
        entrypoint: Path (relative to project root) to the entrypoint file that runs the MCPApp instance.
                    This file must execute the `run()` method on your `MCPApp` instance when invoked directly.
        skip_validate: Skip running the server locally for health/metadata checks.
        server_name: Explicit server name to use when --skip-validate is set.
        server_version: Explicit server version to use when --skip-validate is set.
        secrets: How to upsert secrets before deploy.
        host: Arcade Engine host
        port: Arcade Engine port (optional)
        force_tls: Force TLS connection
        force_no_tls: Disable TLS connection
        debug: Show debug information
    """
    # Step 1: Validate user is logged in
    console.print("\nValidating user is logged in...", style="dim")
    config = validate_and_get_config()
    engine_url = compute_base_url(force_tls, force_no_tls, host, port)
    user_email = config.user.email if config.user else "User"
    console.print(f"✓ {user_email} is logged in", style="green")

    # Step 2: Validate necessary files exist in the correct location
    console.print("\nValidating pyproject.toml exists in current directory...", style="dim")
    current_dir = Path.cwd()
    pyproject_path = current_dir / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(
            f"pyproject.toml not found at {pyproject_path}\n"
            "Please run this command from the root of your MCP server package (the same directory that contains pyproject.toml)."
        )
    console.print(f"✓ pyproject.toml found at {pyproject_path}", style="green")
    console.print("\nValidating entrypoint file exists at the specified location...", style="dim")
    entrypoint_path = current_dir / entrypoint
    if not entrypoint_path.exists():
        raise FileNotFoundError(
            f"Entrypoint file not found at {entrypoint_path}\n"
            "Please specify the correct entrypoint file using the --entrypoint/-e flag.\n"
            "For example: arcade deploy -e src/my_server/server.py"
        )
    console.print(f"✓ Entrypoint file found at {entrypoint_path}", style="green")

    # Step 3: Load .env file from current directory if it exists
    console.print("\nLoading .env file from current directory if it exists...", style="dim")
    env_path = current_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
        console.print(f"✓ Loaded environment from {env_path}", style="green")
    else:
        console.print(f"[!] No .env file found at {env_path}", style="yellow")

    # Step 4: Verify server and extract metadata (or skip if --skip-validate)
    required_secrets_from_validation: set[str] = set()

    if skip_validate:
        console.print("\n[!] Skipping server validation (--skip-validate set)", style="yellow")
        # Use the provided server_name and server_version
        # These are guaranteed to be set due to validation in main.py
        if server_name is None:
            raise ValueError("server_name must be provided when skip_validate is True")
        if server_version is None:
            raise ValueError("server_version must be provided when skip_validate is True")

        console.print(f"✓ Using server name: {server_name}", style="green")
        console.print(f"✓ Using server version: {server_version}", style="green")
    else:
        console.print(
            "\nValidating server is healthy and extracting metadata before deploying...",
            style="dim",
        )
        try:
            server_name, server_version, required_secrets_from_validation = (
                verify_server_and_get_metadata(entrypoint, debug=debug)
            )
        except Exception as e:
            raise ValueError(
                f"Server verification failed: {e}\n"
                "Please ensure your server starts correctly before deploying."
            ) from e

    # Step 5: Determine which secrets to upsert based on --secrets flag
    secrets_to_upsert: set[str] = set()

    if secrets == "skip":
        console.print("\n[!] Skipping secret upload (--secrets skip)", style="yellow")
    elif secrets == "all":
        console.print("\nUploading ALL secrets from .env file...", style="dim")
        secrets_to_upsert = set(load_env_file(str(env_path)).keys())
        if secrets_to_upsert:
            console.print(f"✓ Found {len(secrets_to_upsert)} secret(s) in .env file", style="green")
            upsert_secrets_to_engine(engine_url, secrets_to_upsert, debug)
        else:
            console.print("[!] No secrets found in .env file", style="yellow")
    elif secrets == "auto":
        # Only upload required secrets discovered during validation
        if required_secrets_from_validation:
            console.print(
                f"\nUploading {len(required_secrets_from_validation)} required secret(s) to Arcade...",
                style="dim",
            )
            upsert_secrets_to_engine(engine_url, required_secrets_from_validation, debug)
        else:
            console.print("\n✓ No required secrets found", style="green")

    # Step 6: Create tar.gz archive of current directory
    console.print("\nCreating deployment package...", style="dim")
    try:
        archive_base64 = create_package_archive(current_dir)
        archive_size_kb = len(archive_base64) * 3 / 4 / 1024  # base64 is ~4/3 larger
        console.print(f"✓ Package created ({archive_size_kb:.1f} KB)", style="green")
    except Exception as e:
        raise ValueError(f"Failed to create package archive: {e}") from e

    # Step 7: Send deployment request to engine
    is_update = False
    try:
        toolkit_bundle = ToolkitBundle(
            name=server_name,
            version=server_version,
            bytes=archive_base64,
            type="mcp",
            entrypoint=entrypoint,
        )
        deployment_toolkits = DeploymentToolkits(bundles=[toolkit_bundle])

        if server_already_exists(engine_url, server_name):
            is_update = True
            update_request = UpdateDeploymentRequest(
                description="MCP Server deployed via CLI",
                toolkits=deployment_toolkits,
            )
            update_deployment(engine_url, server_name, update_request.model_dump())
        else:
            create_request = CreateDeploymentRequest(
                name=server_name,
                description="MCP Server deployed via CLI",
                toolkits=deployment_toolkits,
            )
            deploy_server_to_engine(engine_url, create_request.model_dump(), debug)
    except Exception as e:
        raise ValueError(f"Deployment failed: {e}") from e

    # Step 8: Monitor deployment with live status and logs
    final_status, all_logs = asyncio.run(
        _monitor_deployment_with_logs(engine_url, server_name, debug, is_update)
    )

    if final_status == "running":
        console.print("\n✓ Deployment successful! Server is running.", style="bold green")
    elif final_status == "failed":
        console.print("\n✗ Deployment failed. Check logs for details.", style="bold red")

    # Offer to view full deployment logs
    if all_logs and Confirm.ask("\nView full deployment logs?", default=False):  # type: ignore[arg-type]
        with console.pager(styles=True):
            console.print("[bold]Full Deployment Logs[/bold]\n", style="cyan")
            for i, log_line in enumerate(all_logs, 1):
                console.print(f"{i:4d} | {log_line}", style="dim")
