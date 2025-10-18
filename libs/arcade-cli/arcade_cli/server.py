import asyncio

import httpx
import typer
from arcadepy import Arcade, NotFoundError
from arcadepy.types import WorkerHealthResponse, WorkerResponse
from rich.console import Console
from rich.table import Table

from arcade_cli.constants import (
    PROD_ENGINE_HOST,
)
from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import (
    compute_base_url,
    handle_cli_error,
    validate_and_get_config,
)

console = Console()


app = TrackedTyper(
    cls=TrackedTyperGroup,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)

state = {
    "engine_url": compute_base_url(
        host=PROD_ENGINE_HOST, port=None, force_tls=False, force_no_tls=False
    )
}


@app.callback()
def main(
    host: str = typer.Option(
        PROD_ENGINE_HOST,
        "--host",
        "-h",
        help="The Arcade Engine host.",
    ),
    port: int = typer.Option(
        None,
        "--port",
        "-p",
        help="The port of the Arcade Engine host.",
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine.",
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
    ),
) -> None:
    """
    Manage users in the system.
    """
    engine_url = compute_base_url(force_tls, force_no_tls, host, port)
    state["engine_url"] = engine_url


@app.command("list", help="List all servers")
def list_servers(
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show debug information",
    ),
) -> None:
    config = validate_and_get_config()
    base_url = state["engine_url"]
    client = Arcade(api_key=config.api.key, base_url=base_url)
    try:
        servers = client.workers.list(limit=100)
        _print_servers_table(servers.items)
    except Exception as e:
        handle_cli_error("Failed to list servers", e, debug=debug)


@app.command("get", help="Get a server's details")
def get_server(
    server_name: str,
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show debug information",
    ),
) -> None:
    config = validate_and_get_config()
    base_url = state["engine_url"]
    client = Arcade(api_key=config.api.key, base_url=base_url)
    try:
        server = client.workers.get(server_name)
        server_health = client.workers.health(server_name)
        _print_server_details(server, server_health)
    except Exception as e:
        handle_cli_error(f"Failed to get server '{server_name}'", e, debug=debug)


@app.command("enable", help="Enable a server")
def enable_server(
    server_name: str,
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show debug information",
    ),
) -> None:
    config = validate_and_get_config()
    engine_url = state["engine_url"]
    arcade = Arcade(api_key=config.api.key, base_url=engine_url)
    try:
        arcade.workers.update(server_name, enabled=True)
    except Exception as e:
        handle_cli_error(f"Failed to enable worker '{server_name}'", e, debug=debug)


@app.command("disable", help="Disable a server")
def disable_server(
    server_name: str,
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show debug information",
    ),
) -> None:
    config = validate_and_get_config()
    engine_url = state["engine_url"]
    arcade = Arcade(api_key=config.api.key, base_url=engine_url)
    try:
        arcade.workers.update(server_name, enabled=False)
    except Exception as e:
        handle_cli_error(f"Failed to disable worker '{server_name}'", e, debug=debug)


@app.command("delete", help="Delete a server that is managed by Arcade")
def delete_server(
    server_name: str,
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show debug information",
    ),
) -> None:
    config = validate_and_get_config()
    engine_url = state["engine_url"]

    try:
        arcade = Arcade(api_key=config.api.key, base_url=engine_url)
        arcade.workers.delete(server_name)
        console.print(f"✓ Server '{server_name}' deleted successfully", style="green")
    except NotFoundError as e:
        handle_cli_error(
            f"Server '{server_name}' doesn't exist or cannot be deleted", e, debug=debug
        )
    except Exception as e:
        handle_cli_error(
            f"Server '{server_name}' doesn't exist or cannot be deleted", e, debug=debug
        )


@app.command("logs", help="Get logs for a server that is managed by Arcade")
def get_server_logs(
    server_name: str,
    no_stream: bool = typer.Option(
        False,
        "--no-stream",
        "-n",
        is_flag=True,
        help="Do not stream the logs for the server",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show debug information",
    ),
) -> None:
    config = validate_and_get_config()
    headers = {"Authorization": f"Bearer {config.api.key}", "Content-Type": "application/json"}

    if no_stream:
        # Use the non-streaming endpoint
        engine_url = state["engine_url"] + f"/v1/deployments/{server_name}/logs"
        _display_deployment_logs(engine_url, headers, debug=debug)
    else:
        # Use the streaming endpoint
        engine_url = state["engine_url"] + f"/v1/deployments/{server_name}/logs/stream"
        asyncio.run(_stream_deployment_logs(engine_url, headers, debug=debug))


def _display_deployment_logs(engine_url: str, headers: dict, debug: bool) -> None:
    try:
        with httpx.Client() as client:
            response = client.get(engine_url, headers=headers)
            response.raise_for_status()
            logs = response.json()
            for log in logs:
                print(f"[{log['timestamp']}] {log['line']}")
    except httpx.HTTPStatusError as e:
        handle_cli_error(
            f"Failed to fetch logs: {e.response.status_code} {e.response.text}", debug=debug
        )
    except Exception as e:
        handle_cli_error(f"Error fetching logs: {e}", debug=debug)


async def _stream_deployment_logs(engine_url: str, headers: dict, debug: bool) -> None:
    try:
        async with (
            httpx.AsyncClient(timeout=None) as client,  # noqa: S113 - expected indefinite log stream
            client.stream("GET", engine_url, headers=headers) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                print(line)
    except httpx.HTTPStatusError as e:
        handle_cli_error(f"Failed to stream logs: {e.response.status_code}", debug=debug)
    except Exception as e:
        handle_cli_error(f"Error streaming logs: {e}", debug=debug)


def _print_servers_table(servers: list[WorkerResponse]) -> None:
    if not servers:
        console.print("No servers found", style="bold red")
        return

    table = Table(title="Servers")
    table.add_column("Name")
    table.add_column("Enabled")
    table.add_column("Host")
    table.add_column("Managed by Arcade")

    for server in servers:
        if server.id is None:
            continue
        uri = server.http.uri if server.http and server.http.uri else "N/A"
        table.add_row(
            server.id,
            str(server.enabled),
            uri,
            str(server.managed),
        )
    console.print(table)


def _print_server_details(server: WorkerResponse, server_health: WorkerHealthResponse) -> None:
    table = Table(title="Server Details")
    table.add_column("Name")
    table.add_column("Enabled")
    table.add_column("Is Healthy")
    table.add_column("Host")
    table.add_column("Managed by Arcade")
    uri = server.http.uri if server.http and server.http.uri else "N/A"
    table.add_row(
        server.id, str(server.enabled), str(server_health.healthy), uri, str(server.managed)
    )
    console.print(table)
