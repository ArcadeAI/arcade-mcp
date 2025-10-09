"""
Deploy MCP servers directly to Arcade Engine.

This module handles the deployment of MCP servers to Arcade Engine via the /v1/deployments endpoint.
It is completely independent from the legacy arcade_cli.deployment module to allow for clean separation.
"""

import base64
import io
import os
import random
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import httpx
from arcade_core.config_model import Config
from dotenv import load_dotenv
from rich.console import Console

from arcade_cli.utils import compute_base_url, validate_and_get_config

console = Console()


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
        """Filter for files/directories to exclude from the archive."""
        name = tarinfo.name

        # Exclude hidden files and directories
        parts = Path(name).parts
        if any(part.startswith(".") for part in parts):
            return None

        # Exclude __pycache__ directories
        if "__pycache__" in parts:
            return None

        # Exclude .egg-info directories
        if any(part.endswith(".egg-info") for part in parts):
            return None

        # Exclude dist and build directories
        if "dist" in parts or "build" in parts:
            return None

        # Exclude files ending with .lock
        if name.endswith(".lock"):
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


def verify_server_and_get_metadata(
    entrypoint: str, debug: bool = False
) -> tuple[str, str, set[str]]:
    """
    Start the server, verify it's healthy, and extract metadata.

    This function:
    1. Picks a random port
    2. Starts the server with environment variables set
    3. Waits for the server to become healthy
    4. Extracts server name and version via POST /mcp
    5. Extracts required secrets via GET /worker/tools
    6. Stops the server
    7. Returns the metadata

    Args:
        entrypoint: Path to the entrypoint file
        debug: Whether to show debug information

    Returns:
        Tuple of (server_name, server_version, required_secrets_set)

    Raises:
        ValueError: If the server fails to start or metadata extraction fails
    """
    console.print("\nVerifying server and extracting metadata...", style="dim")

    port = random.randint(8000, 9000)  # noqa: S311

    # Set environment variables to override app.run() settings
    env = {
        **os.environ,
        "ARCADE_SERVER_HOST": "localhost",
        "ARCADE_SERVER_PORT": str(port),
        "ARCADE_SERVER_TRANSPORT": "http",
        "ARCADE_AUTH_DISABLED": "true",
    }

    # Start the server
    cmd = [sys.executable, entrypoint]
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    if debug:
        console.print(f"  Started server on port {port}", style="dim")

    # Check if process immediately failed
    time.sleep(0.5)
    if process.poll() is not None:
        _, stderr = process.communicate()
        error_msg = stderr.strip() if stderr else "Unknown error"
        raise ValueError(f"Server process exited immediately: {error_msg}")

    # Poll health endpoint
    base_url = f"http://127.0.0.1:{port}"
    health_url = f"{base_url}/worker/health"
    start_time = time.time()
    is_healthy = False

    while time.time() - start_time < 30:
        try:
            response = httpx.get(health_url, timeout=2.0)
            if response.status_code == 200:
                is_healthy = True
                break
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        except Exception:
            pass
        time.sleep(0.5)

    if not is_healthy:
        # Server didn't become healthy
        process.terminate()
        try:
            _, stderr = process.communicate(timeout=2)
            error_msg = stderr.strip() if stderr else "Server failed to become healthy"
        except subprocess.TimeoutExpired:
            process.kill()
            error_msg = "Server failed to become healthy within 30 seconds"
        raise ValueError(error_msg)

    console.print("✓ Server is healthy", style="green")

    try:
        # Extract server name and version via POST /mcp
        mcp_url = f"{base_url}/mcp"
        initialize_request = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "capabilities": {},
                "clientInfo": {"name": "arcade-deploy-client", "version": "1.0.0"},
                "protocolVersion": "2025-06-18",
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            mcp_response = httpx.post(
                mcp_url, json=initialize_request, headers=headers, timeout=10.0
            )
            mcp_response.raise_for_status()
            mcp_data = mcp_response.json()

            server_name = mcp_data["result"]["serverInfo"]["name"]
            server_version = mcp_data["result"]["serverInfo"]["version"]

            if debug:
                console.print(
                    f"  Extracted name: {server_name}, version: {server_version}", style="dim"
                )
        except Exception as e:
            raise ValueError(f"Failed to extract server info from /mcp endpoint: {e}") from e

        # Extract required secrets via GET /worker/tools
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
                        if "key" in secret and secret["key"]:
                            required_secrets.add(secret["key"])

            if debug:
                if required_secrets:
                    console.print(
                        f"  Found {len(required_secrets)} required secret(s)", style="dim"
                    )
                else:
                    console.print("  No secrets required", style="dim")

        except Exception as e:
            raise ValueError(
                f"Failed to extract tool secrets from /worker/tools endpoint: {e}"
            ) from e

    finally:
        # Always stop the server
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        if debug:
            console.print("  Server stopped", style="dim")

    return server_name, server_version, required_secrets


def upsert_secrets_to_engine(
    engine_url: str, api_key: str, secrets: set[str], debug: bool = False
) -> None:
    """
    Upsert secrets to the Arcade Engine.

    Args:
        engine_url: The base URL of the Arcade Engine
        api_key: The API key for authentication
        secrets: Set of secret keys to upsert
        debug: Whether to show debug information
    """
    if not secrets:
        return

    console.print(f"\nRequired secrets: {', '.join(sorted(secrets))}", style="dim")

    client = httpx.Client(base_url=engine_url, headers={"Authorization": f"Bearer {api_key}"})

    for secret_key in sorted(secrets):
        secret_value = os.getenv(secret_key)

        if debug:
            if secret_value:
                console.print(
                    f"  Found secret '{secret_key}' in environment (value ends with ...{secret_value[-4:]})",
                    style="dim",
                )
            else:
                console.print(
                    f"  Secret '{secret_key}' not found in environment", style="dim yellow"
                )

        if not secret_value:
            console.print(
                f"⚠️  Secret '{secret_key}' not found in environment, skipping.",
                style="yellow",
            )
            continue

        try:
            # Upsert secret to engine
            response = client.put(
                f"/v1/admin/secrets/{secret_key}",
                json={"description": "Secret set via CLI", "value": secret_value},
                timeout=30,
            )
            response.raise_for_status()
            console.print(f"✓ Secret '{secret_key}' uploaded", style="dim green")
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
    engine_url: str, api_key: str, deployment_request: dict, debug: bool = False
) -> dict:
    """
    Deploy the server to Arcade Engine.

    Args:
        engine_url: The base URL of the Arcade Engine
        api_key: The API key for authentication
        deployment_request: The deployment request payload
        debug: Whether to show debug information

    Returns:
        The response JSON from the deployment API

    Raises:
        httpx.HTTPStatusError: If the deployment request fails
        httpx.ConnectError: If connection to the engine fails
    """
    client = httpx.Client(
        base_url=engine_url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=360,
    )

    try:
        response = client.post("/v1/deployments", json=deployment_request)
        response.raise_for_status()
        return response.json()
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
    host: str,
    port: int | None,
    force_tls: bool,
    force_no_tls: bool,
    debug: bool,
) -> None:
    """
    Main logic for deploying an MCP server to Arcade Engine.

    Args:
        entrypoint: Path to the entrypoint file containing MCPApp
        host: Arcade Engine host
        port: Arcade Engine port (optional)
        force_tls: Force TLS connection
        force_no_tls: Disable TLS connection
        debug: Show debug information
    """
    # Step 1: Validate user is logged in
    config = validate_and_get_config()
    engine_url = compute_base_url(force_tls, force_no_tls, host, port)

    # Step 2: Validate pyproject.toml exists in current directory
    current_dir = Path.cwd()
    pyproject_path = current_dir / "pyproject.toml"

    if not pyproject_path.exists():
        raise FileNotFoundError(
            f"pyproject.toml not found in current directory: {current_dir}\n"
            "Please run this command from the root of your MCP server package."
        )

    # Step 2.5: Load .env file from current directory if it exists
    env_path = current_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
        if debug:
            console.print(f"  Loaded environment from {env_path}", style="dim")

    # Step 3: Verify server and extract metadata
    try:
        server_name, server_version, required_secrets = verify_server_and_get_metadata(
            entrypoint, debug=debug
        )
    except Exception as e:
        raise ValueError(
            f"Server verification failed: {e}\n"
            "Please ensure your server starts correctly before deploying."
        ) from e

    console.print(f"✓ Found server: {server_name} v{server_version}", style="green")

    # Step 4: Upsert secrets to engine
    if required_secrets:
        console.print(f"\nDiscovered {len(required_secrets)} required secret(s)", style="dim")
        upsert_secrets_to_engine(engine_url, config.api.key, required_secrets, debug)
    else:
        console.print("\nNo secrets required", style="dim")

    # Step 5: Create tar.gz archive of current directory
    console.print("\nCreating deployment package...", style="dim")
    try:
        archive_base64 = create_package_archive(current_dir)
        archive_size_kb = len(archive_base64) * 3 / 4 / 1024  # base64 is ~4/3 larger
        console.print(f"✓ Package created ({archive_size_kb:.1f} KB)", style="green")
    except Exception as e:
        raise ValueError(f"Failed to create package archive: {e}") from e

    # Step 6: Build deployment request payload
    deployment_request = {
        "name": server_name,
        "type": "mcp",
        "entrypoint": entrypoint,
        "description": "MCP Server deployed via CLI",
        "toolkits": {
            "bundles": [
                {
                    "name": server_name,
                    "version": server_version,
                    "bytes": archive_base64,
                }
            ]
        },
    }

    # Step 7: Send deployment request to engine
    console.print("\nDeploying to Arcade Engine...", style="dim")
    try:
        response = deploy_server_to_engine(engine_url, config.api.key, deployment_request, debug)
    except Exception as e:
        raise ValueError(f"Deployment failed: {e}") from e

    # Step 8: Display success message with deployment details
    console.print(
        f"✓ Server '{server_name}' v{server_version} deployed successfully", style="bold green"
    )
    console.print(f"\nDeployment URL: {engine_url}/v1/deployments/{server_name}", style="dim")

    if debug and response:
        console.print("\nDeployment response:", style="dim")
        console.print(response)
