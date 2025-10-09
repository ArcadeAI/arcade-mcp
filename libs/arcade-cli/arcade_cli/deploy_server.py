"""
Deploy MCP servers directly to Arcade Engine.

This module handles the deployment of MCP servers to Arcade Engine via the /v1/deployments endpoint.
It is completely independent from the legacy arcade_cli.deployment module to allow for clean separation.
"""

import ast
import base64
import importlib.util
import io
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from rich.console import Console

from arcade_cli.utils import compute_base_url, validate_and_get_config

if TYPE_CHECKING:
    from arcade_mcp_server.mcp_app import MCPApp

console = Console()


def validate_entrypoint_structure(entrypoint: str) -> None:
    """
    Validate that the entrypoint file has proper structure with if __name__ == "__main__".

    This ensures that app.run() or similar blocking calls are protected and won't
    block the import when we load the MCPApp for inspection.

    Args:
        entrypoint: Path to the entrypoint file

    Raises:
        ValueError: If the file structure is invalid
    """
    entrypoint_path = Path(entrypoint).resolve()

    try:
        with open(entrypoint_path) as f:
            source = f.read()
    except Exception as e:
        raise ValueError(f"Failed to read entrypoint file: {e}") from e

    try:
        tree = ast.parse(source, filename=str(entrypoint_path))
    except SyntaxError as e:
        raise ValueError(f"Syntax error in entrypoint file: {e}") from e

    # Check if there's an if __name__ == "__main__" block
    has_main_block = False

    for node in ast.walk(tree):
        # Check for if __name__ == "__main__" pattern
        if isinstance(node, ast.If):
            if _is_main_guard(node):
                has_main_block = True
                break

    if not has_main_block:
        raise ValueError(
            f"Entrypoint file '{entrypoint}' must have an 'if __name__ == \"__main__\"' block that runs the server.\n\n"
            "The entrypoint should be structured like:\n\n"
            "  app = MCPApp(name='my_server', version='1.0.0')\n\n"
            "  @app.tool\n"
            "  def my_tool():\n"
            "      ...\n\n"
            "  if __name__ == '__main__':\n"
            "      app.run()\n\n"
        )


def _is_main_guard(node: ast.If) -> bool:
    """Check if an If node is an if __name__ == '__main__' guard."""
    if not isinstance(node.test, ast.Compare):
        return False

    compare = node.test
    if not isinstance(compare.left, ast.Name):
        return False

    if compare.left.id != "__name__":
        return False

    if len(compare.ops) != 1 or not isinstance(compare.ops[0], ast.Eq):
        return False

    if len(compare.comparators) != 1:
        return False

    comparator = compare.comparators[0]
    if isinstance(comparator, ast.Constant):
        return comparator.value == "__main__"
    elif isinstance(comparator, ast.Str):  # Python 3.7 compatibility
        return comparator.s == "__main__"

    return False


def load_mcp_app_from_entrypoint(entrypoint: str) -> "MCPApp":
    """
    Dynamically import the entrypoint file and extract the MCPApp instance.

    Args:
        entrypoint: Relative path to the entrypoint file (e.g., "server.py")

    Returns:
        The MCPApp instance found in the module

    Raises:
        FileNotFoundError: If entrypoint doesn't exist
        ValueError: If no MCPApp instance is found or multiple are found
    """
    from arcade_mcp_server.mcp_app import MCPApp

    entrypoint_path = Path(entrypoint).resolve()

    if not entrypoint_path.exists():
        raise FileNotFoundError(f"Entrypoint file not found: {entrypoint}")

    if not entrypoint_path.is_file():
        raise ValueError(f"Entrypoint must be a file, not a directory: {entrypoint}")

    # Create a unique module name to avoid conflicts
    module_name = f"_arcade_deploy_{entrypoint_path.stem}"

    # Load the module from the file path
    spec = importlib.util.spec_from_file_location(module_name, entrypoint_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load module spec from {entrypoint}")

    module = importlib.util.module_from_spec(spec)

    # Add to sys.modules temporarily so relative imports work
    sys.modules[module_name] = module

    try:
        # Execute the module
        spec.loader.exec_module(module)
    except Exception as e:
        # Clean up sys.modules on error
        sys.modules.pop(module_name, None)
        raise ValueError(f"Failed to import entrypoint module: {e}") from e

    # Find all MCPApp instances in the module
    mcp_apps = []
    for name, obj in vars(module).items():
        if isinstance(obj, MCPApp):
            mcp_apps.append((name, obj))

    # Clean up sys.modules
    sys.modules.pop(module_name, None)

    if len(mcp_apps) == 0:
        raise ValueError(f"No MCPApp instance found in {entrypoint}")

    if len(mcp_apps) > 1:
        app_names = ", ".join(name for name, _ in mcp_apps)
        raise ValueError(
            f"Multiple MCPApp instances found in {entrypoint}: {app_names}. "
            "Please ensure only one MCPApp instance is defined."
        )

    _, app = mcp_apps[0]
    return app


def get_required_secrets(app: "MCPApp") -> set[str]:  # type: ignore
    """
    Extract all required secret keys from the MCPApp's catalog.

    Args:
        app: The MCPApp instance

    Returns:
        A set of secret key names required by all tools
    """
    required_secrets = set()

    # Iterate through all tools in the catalog
    for tool in app._catalog:
        # Check if tool has secret requirements
        if tool.definition.requirements and tool.definition.requirements.secrets:
            for secret in tool.definition.requirements.secrets:
                if secret.key:
                    required_secrets.add(secret.key)

    return required_secrets


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


def start_local_server(entrypoint: str, port: int = 8000) -> subprocess.Popen:
    """
    Start the MCP server locally as a subprocess.

    Args:
        entrypoint: Path to the entrypoint file
        port: Port to run the server on

    Returns:
        The subprocess handle

    Raises:
        ValueError: If the server process fails to start
    """
    # Use Python to run the entrypoint file
    cmd = [sys.executable, entrypoint]

    # Start the process, capturing stdout and stderr
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={**os.environ, "PORT": str(port)},
    )

    return process


def check_server_health(port: int = 8000, timeout: int = 30, check_interval: float = 0.5) -> bool:
    """
    Poll the server's health endpoint until it responds or times out.

    Args:
        port: Port the server is running on
        timeout: Maximum time to wait in seconds
        check_interval: Time between health checks in seconds

    Returns:
        True if the server becomes healthy, False otherwise
    """
    health_url = f"http://127.0.0.1:{port}/worker/health"
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = httpx.get(health_url, timeout=2.0)
            if response.status_code == 200:
                return True
        except (httpx.ConnectError, httpx.TimeoutException):
            # Server not ready yet, continue polling
            pass
        except Exception:
            # Unexpected error, but continue polling
            pass

        time.sleep(check_interval)

    return False


def stop_local_server(process: subprocess.Popen) -> None:
    """
    Stop the local MCP server process.

    Args:
        process: The subprocess handle
    """
    try:
        # Try graceful shutdown first
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Force kill if graceful shutdown fails
            process.kill()
            process.wait()
    except Exception:
        # If anything goes wrong, try to kill it
        try:
            process.kill()
        except Exception:
            pass


def verify_server_starts(entrypoint: str, port: int = 8000, debug: bool = False) -> None:
    """
    Verify that the server starts and becomes healthy.

    Args:
        entrypoint: Path to the entrypoint file
        port: Port to run the server on
        debug: Whether to show debug information

    Raises:
        ValueError: If the server fails to start or become healthy
    """
    console.print("\nVerifying server starts correctly...", style="dim")

    # Start the server
    try:
        process = start_local_server(entrypoint, port)
    except Exception as e:
        raise ValueError(f"Failed to start server process: {e}") from e

    # Check if process immediately failed
    time.sleep(0.5)
    if process.poll() is not None:
        # Process already exited
        _, stderr = process.communicate()
        error_msg = stderr.strip() if stderr else "Unknown error"
        raise ValueError(f"Server process exited immediately: {error_msg}")

    # Poll health endpoint
    try:
        is_healthy = check_server_health(port=port, timeout=30)

        if not is_healthy:
            # Server didn't become healthy in time
            stop_local_server(process)

            # Try to get error output
            try:
                _, stderr = process.communicate(timeout=2)
                error_msg = stderr.strip() if stderr else "Server failed to become healthy"
            except subprocess.TimeoutExpired:
                error_msg = "Server failed to become healthy within 30 seconds"

            raise ValueError(error_msg)

        # Server is healthy!
        console.print("✓ Server started successfully and is healthy", style="green")

        # Stop the server
        stop_local_server(process)

        if debug:
            console.print("  Server verification complete, process stopped", style="dim")

    except ValueError:
        # Re-raise verification errors
        raise
    except Exception as e:
        # Cleanup and raise
        stop_local_server(process)
        raise ValueError(f"Error during server verification: {e}") from e


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

    # Step 3: Validate entrypoint structure
    try:
        validate_entrypoint_structure(entrypoint)
    except Exception as e:
        raise ValueError(f"Invalid entrypoint structure: {e}") from e

    # Step 4: Verify server starts and is healthy
    try:
        verify_server_starts(entrypoint, port=8000, debug=debug)
    except Exception as e:
        raise ValueError(
            f"Server verification failed: {e}\n"
            "Please ensure your server starts correctly before deploying."
        ) from e

    # Step 5: Load MCPApp from entrypoint
    console.print(f"\nLoading MCP server from {entrypoint}...", style="dim")
    try:
        app = load_mcp_app_from_entrypoint(entrypoint)
    except Exception as e:
        raise ValueError(f"Failed to load MCPApp from {entrypoint}: {e}") from e

    # Step 6: Get server name and version from app
    server_name = app.name
    server_version = app.version
    tool_count = len(list(app._catalog))

    console.print(f"✓ Found server: {server_name} v{server_version}", style="green")
    console.print(f"  Discovered {tool_count} tool(s) in catalog", style="dim")

    # Step 7: Discover required secrets
    required_secrets = get_required_secrets(app)

    # Step 8: Upsert secrets to engine
    if required_secrets:
        upsert_secrets_to_engine(engine_url, config.api.key, required_secrets, debug)
    else:
        console.print("\nNo secrets required", style="dim")

    # Step 9: Create tar.gz archive of current directory
    console.print("\nCreating deployment package...", style="dim")
    try:
        archive_base64 = create_package_archive(current_dir)
        # Calculate size in MB
        archive_size_mb = len(archive_base64) * 3 / 4 / 1024 / 1024  # base64 is ~4/3 larger
        console.print(f"✓ Package created ({archive_size_mb:.1f} MB)", style="green")
    except Exception as e:
        raise ValueError(f"Failed to create package archive: {e}") from e

    # Step 10: Build deployment request payload
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

    # Step 11: Send deployment request to engine
    console.print("\nDeploying to Arcade Engine...", style="dim")
    try:
        response = deploy_server_to_engine(engine_url, config.api.key, deployment_request, debug)
    except Exception as e:
        raise ValueError(f"Deployment failed: {e}") from e

    # Step 12: Display success message with deployment details
    console.print(
        f"✓ Server '{server_name}' v{server_version} deployed successfully", style="bold green"
    )
    console.print(f"\nDeployment URL: {engine_url}/v1/deployments/{server_name}", style="dim")
    console.print(f"Tools: {tool_count} tool(s) deployed", style="dim")

    if debug and response:
        console.print("\nDeployment response:", style="dim")
        console.print(response)
