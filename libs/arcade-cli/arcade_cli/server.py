import asyncio
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
import typer
from arcade_core.constants import PROD_ENGINE_HOST
from arcadepy import NotFoundError
from arcadepy.types import WorkerHealthResponse, WorkerResponse
from dateutil import parser
from rich.console import Console
from rich.table import Table

from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import (
    compute_base_url,
    get_arcade_client,
    get_auth_headers,
    get_org_scoped_url,
    handle_cli_error,
)

console = Console()


def _format_timestamp_to_local(timestamp_str: str) -> str:
    """
    Convert a UTC timestamp string to local timezone format.

    Args:
        timestamp_str: UTC timestamp in format "2025-10-22T21:08:23.508906574Z"

    Returns:
        Formatted timestamp string in local timezone
    """
    try:
        # Parse the UTC timestamp and convert to local timezone
        utc_dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        local_dt = utc_dt.astimezone()
        return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except (ValueError, TypeError):
        # If parsing fails, return the original timestamp
        return timestamp_str


def _parse_time_string(time_str: str) -> datetime:
    """
    Parse a time string that can be either relative (e.g., "1h", "42m", "2d")
    or absolute (e.g., "2025-10-03T12:24:36Z").

    Args:
        time_str: Time string in relative or absolute format

    Returns:
        datetime object in UTC timezone

    Raises:
        ValueError: If the time string cannot be parsed
    """
    if not time_str:
        raise ValueError("Time string cannot be empty")

    # Handle relative time formats (e.g., "1h", "42m", "2d", "0m")
    relative_pattern = r"^(\d+)([smhd])$"
    match = re.match(relative_pattern, time_str.lower())

    if match:
        value = int(match.group(1))
        unit = match.group(2)

        now = datetime.now(timezone.utc)

        if unit == "s":
            delta = timedelta(seconds=value)
        elif unit == "m":
            delta = timedelta(minutes=value)
        elif unit == "h":
            delta = timedelta(hours=value)
        elif unit == "d":
            delta = timedelta(days=value)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

        return now - delta

    # Handle absolute time formats using dateutil parser
    try:
        parsed_dt = parser.parse(time_str)

        # Ensure timezone awareness
        if parsed_dt.tzinfo is None:
            # Assume UTC if no timezone info
            parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC
            parsed_dt = parsed_dt.astimezone(timezone.utc)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Unable to parse time string '{time_str}': {e}")

    return parsed_dt


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
    base_url = state["engine_url"]
    client = get_arcade_client(base_url)
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
    base_url = state["engine_url"]
    client = get_arcade_client(base_url)
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
    engine_url = state["engine_url"]
    arcade = get_arcade_client(engine_url)
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
    engine_url = state["engine_url"]
    arcade = get_arcade_client(engine_url)
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
    engine_url = state["engine_url"]

    try:
        arcade = get_arcade_client(engine_url)
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
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        is_flag=True,
        help="Follow (stream) the log output in real-time",
        rich_help_panel="Streaming Options",
    ),
    since: Optional[str] = typer.Option(
        None,
        "--since",
        "-s",
        help="Show logs since timestamp (e.g., 2025-10-03T12:24:36Z) or relative (e.g., 42m for 42 minutes ago). Defaults to 1h (1 hour ago) for non-streaming, 0s (now) for streaming.",
        rich_help_panel="Time Range Options",
    ),
    until: Optional[str] = typer.Option(
        None,
        "--until",
        "-u",
        help="Show logs until timestamp (e.g., 2025-10-03T12:24:36Z) or relative (e.g., 42m for 42 minutes ago). Defaults to 0s (now).",
        rich_help_panel="Time Range Options",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        "-d",
        help="Show debug information",
    ),
) -> None:
    auth_headers = get_auth_headers()
    headers = {**auth_headers, "Content-Type": "application/json"}

    # Set defaults based on whether we're following or not
    if since is None:
        since = "0s" if follow else "1h"
    if until is None:
        until = "0s"

    try:
        # Parse time strings to UTC datetime objects
        since_dt = _parse_time_string(since)
        until_dt = _parse_time_string(until)

        # Validate that since is before until
        if since_dt >= until_dt:
            raise ValueError(f"'since' time ({since}) must be before 'until' time ({until})")  # noqa: TRY301
    except ValueError as e:
        handle_cli_error(f"Invalid time format: {e}", debug=debug)

    base_url = state["engine_url"]

    if follow:
        # Use the streaming endpoint
        logs_url = get_org_scoped_url(base_url, f"/deployments/{server_name}/logs/stream")
        asyncio.run(_stream_deployment_logs(logs_url, headers, since_dt, until_dt, debug=debug))
    else:
        # Use the non-streaming endpoint
        logs_url = get_org_scoped_url(base_url, f"/deployments/{server_name}/logs")
        _display_deployment_logs(logs_url, headers, since_dt, until_dt, debug=debug)


def _display_deployment_logs(
    engine_url: str, headers: dict, since: datetime, until: datetime, debug: bool
) -> None:
    try:
        with httpx.Client() as client:
            params = {"start_time_utc": since.isoformat(), "end_time_utc": until.isoformat()}
            response = client.get(engine_url, headers=headers, params=params)
            response.raise_for_status()
            logs = response.json()
            for log in logs:
                formatted_timestamp = _format_timestamp_to_local(log["timestamp"])
                print(f"[{formatted_timestamp}] {log['line']}")
    except httpx.HTTPStatusError as e:
        handle_cli_error(
            f"Failed to fetch logs: {e.response.status_code} {e.response.text}", debug=debug
        )
    except Exception as e:
        handle_cli_error(f"Error fetching logs: {e}", debug=debug)


async def _stream_deployment_logs(
    engine_url: str, headers: dict, since: datetime, until: datetime, debug: bool
) -> None:
    try:
        async with (
            httpx.AsyncClient(timeout=None) as client,  # noqa: S113 - expected indefinite log stream
            client.stream(
                "GET",
                engine_url,
                headers=headers,
                params={"start_time_utc": since.isoformat(), "end_time_utc": until.isoformat()},
            ) as response,
        ):
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue

                # Handle SSE format: "data: {json}"
                if line.startswith("data: "):
                    try:
                        data = json.loads(line[6:])
                        timestamp_str = data.get("Timestamp", "")
                        log_line = data.get("Line", "")
                        formatted_timestamp = _format_timestamp_to_local(timestamp_str)
                        print(f"[{formatted_timestamp}] {log_line}")
                    except (json.JSONDecodeError, KeyError, IndexError):
                        print(line)
                else:
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
