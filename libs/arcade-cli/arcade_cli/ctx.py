"""Context Box CLI commands — arcade ctx."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from arcade_cli.console import console
from arcade_cli.context_box_client import ContextBoxClient, ContextBoxError, get_engine_url
from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup

app = TrackedTyper(
    cls=TrackedTyperGroup,
    name="ctx",
    help="Manage context boxes",
    no_args_is_help=True,
)


def _get_client() -> ContextBoxClient:
    """Create a ContextBoxClient from environment."""
    base_url = get_engine_url()
    api_key = os.environ.get("ARCADE_API_KEY", "")
    headers = {"Authorization": f"Bearer {api_key}"}
    return ContextBoxClient(base_url, headers)


def _unwrap_items(response: dict | list) -> list:
    """Unwrap API response — handles both {items: [...]} and raw list formats."""
    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("items", [])
    return []


def _resolve_box(client: ContextBoxClient, urn: str) -> dict:
    """Resolve a URN to a box, handling errors."""
    try:
        return client.resolve_urn(urn)
    except ContextBoxError as e:
        if e.status_code == 404:
            console.print(
                f"Error: Box not found: {urn}. Use 'arcade ctx list' to see available boxes.",
                style="bold red",
            )
        else:
            console.print(f"Error: {e.message}", style="bold red")
        raise typer.Exit(code=1) from e


def _detect_agent() -> str | None:
    """Auto-detect which AI agent is installed."""
    if Path.home().joinpath(".claude").exists():
        return "claude"
    if Path.cwd().joinpath(".cursor").exists():
        return "cursor"
    if Path.cwd().joinpath(".windsurf").exists():
        return "windsurf"
    return None


def _format_size(size_bytes: int) -> str:
    """Format byte count to human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


# =====================================================================
# Task 1.2: arcade ctx create
# =====================================================================


@app.command()
def create(
    name: str = typer.Argument(..., help="Box name in owner/name format"),
    import_files: Optional[list[Path]] = typer.Option(
        None, "--import", "-i", help="Files to import as knowledge"
    ),
    template: Optional[str] = typer.Option(None, "--template", help="Template URN"),
    description: str = typer.Option("", "--description", "-d", help="Box description"),
    classification: str = typer.Option(
        "PRIVATE", "--classification", "-c", help="PRIVATE, INTERNAL, or PUBLIC"
    ),
    draft: bool = typer.Option(False, "--draft", help="Create in draft status"),
) -> None:
    """Create a new context box."""
    client = _get_client()
    status = "draft" if draft else "active"

    try:
        box = client.create_box(name, description, classification, status)
    except ContextBoxError as e:
        console.print(f"Error: Failed to create box: {e.status_code} - {e.message}", style="bold red")
        raise typer.Exit(code=1) from e

    urn = box.get("urn", f"urn:arcade:ctx:{name}")
    console.print(f"Created context box: {urn}")
    console.print(f"  Status: {box.get('status', status)}")
    console.print(f"  Classification: {box.get('classification', classification)}")

    if import_files:
        console.print(f"\nImported {len(import_files)} file(s):")
        for file_path in import_files:
            if not file_path.exists():
                console.print(f"  Error: File not found: {file_path}", style="bold red")
                continue
            try:
                result = client.upload_knowledge(box["id"], file_path)
                size = _format_size(file_path.stat().st_size)
                mime = result.get("mime_type", "unknown")
                console.print(f"  {file_path.name} ({mime}, {size})")
            except ContextBoxError as e:
                console.print(
                    f"  Error uploading {file_path.name}: {e.message}", style="bold red"
                )

    console.print(f"\nBox ID: {box['id']}")


# =====================================================================
# Task 1.3: arcade ctx connect
# =====================================================================


@app.command()
def connect(
    urn: str = typer.Argument(..., help="Box URN to connect to"),
    agent: Optional[str] = typer.Option(
        None, "--agent", "-a", help="Agent: claude, cursor, windsurf"
    ),
    gateway_url: Optional[str] = typer.Option(None, "--gateway-url", help="Gateway URL override"),
    config_path: Optional[Path] = typer.Option(None, "--config-path", help="Config file path"),
) -> None:
    """Connect an AI agent to a context box."""
    client = _get_client()

    console.print("Resolving box...")
    box = _resolve_box(client, urn)
    box_name = box.get("name", urn.split(":")[-1])
    console.print(f"  Found: {urn} ({box.get('status', 'unknown')})")

    detected_agent = agent
    if not detected_agent:
        console.print("\nDetecting agent...")
        detected_agent = _detect_agent()
        if not detected_agent:
            console.print(
                "Error: No supported agent detected. Use --agent to specify one of: claude, cursor, windsurf",
                style="bold red",
            )
            raise typer.Exit(code=1)
        console.print(f"  {detected_agent.title()} detected")
    else:
        console.print(f"\nUsing agent: {detected_agent}")

    # Build MCP config
    base_url = gateway_url or get_engine_url()
    parts = box_name.split("/")
    owner = parts[0] if len(parts) > 1 else "default"
    box_short = parts[1] if len(parts) > 1 else parts[0]
    mcp_url = f"{base_url}/mcp/ctx/{owner}/{box_short}/context-box"
    server_name = f"context-box-{owner}-{box_short}"
    api_key = os.environ.get("ARCADE_API_KEY", "")

    mcp_entry = {"url": mcp_url}
    if api_key:
        mcp_entry["headers"] = {"Authorization": f"Bearer {api_key}"}

    # Determine config path
    if not config_path:
        if detected_agent == "claude":
            config_path = Path.cwd() / ".mcp.json"
        elif detected_agent == "cursor":
            config_path = Path.cwd() / ".cursor" / "mcp.json"
        elif detected_agent == "windsurf":
            config_path = Path.cwd() / ".windsurf" / "mcp.json"
        else:
            config_path = Path.cwd() / ".mcp.json"

    console.print("\nConfiguring MCP...")
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config: dict = {}
    if config_path.exists():
        config = json.loads(config_path.read_text())

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    if server_name in config["mcpServers"]:
        console.print(
            f"Note: {detected_agent} is already connected to {urn}. Restart to apply any changes."
        )

    config["mcpServers"][server_name] = mcp_entry
    config_path.write_text(json.dumps(config, indent=2))
    console.print(f"  Wrote {config_path}")

    console.print(f"\nDone. Restart {detected_agent.title()} to connect.")
    console.print(f"MCP endpoint: {mcp_url}")


# =====================================================================
# Task 1.4: arcade ctx list + arcade ctx status
# =====================================================================


@app.command("list")
def list_boxes(
    format: str = typer.Option("table", "--format", "-f", help="Output format: table or json"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max boxes to return"),
    offset: int = typer.Option(0, "--offset", "-o", help="Offset for pagination"),
) -> None:
    """List all context boxes."""
    client = _get_client()

    try:
        result = client.list_boxes(limit=limit, offset=offset)
    except ContextBoxError as e:
        console.print(f"Error: {e.message}", style="bold red")
        raise typer.Exit(code=1) from e

    items = result.get("items", [])
    total = result.get("total", 0)

    if format == "json":
        console.print(json.dumps(result))
        return

    if not items:
        console.print("No context boxes found.")
        return

    table = Table()
    table.add_column("NAME")
    table.add_column("URN")
    table.add_column("STATUS")

    for box in items:
        table.add_row(
            box.get("name", ""),
            box.get("urn", ""),
            box.get("status", ""),
        )

    console.print(table)
    page = (offset // limit) + 1 if limit > 0 else 1
    console.print(f"\nShowing {len(items)} of {total} boxes (page {page})")


@app.command()
def status(
    urn: str = typer.Argument(..., help="Box URN"),
) -> None:
    """Show detailed status of a context box."""
    client = _get_client()
    box = _resolve_box(client, urn)
    box_id = box["id"]

    console.print(f"Context Box: {box.get('urn', urn)}")
    console.print(f"  Status: {box.get('status', 'unknown')}")
    console.print(f"  Classification: {box.get('classification', 'PRIVATE')}")
    if box.get("created_at"):
        console.print(f"  Created: {box['created_at']}")
    if box.get("description"):
        console.print(f"  Description: {box['description']}")

    # Knowledge
    try:
        knowledge = client.list_knowledge(box_id)
        items = _unwrap_items(knowledge)
        console.print(f"\n  Knowledge: {len(items)} items")
        for item in items[:5]:
            console.print(f"    {item.get('uri', 'unknown')}")
        if len(items) > 5:
            console.print(f"    ... and {len(items) - 5} more")
    except ContextBoxError:
        pass

    # Memory
    try:
        memory = client.list_memory(box_id)
        items = _unwrap_items(memory)
        console.print(f"\n  Memory: {len(items)} entries")
        for item in items[:5]:
            console.print(f"    {item.get('key', '?')} = {item.get('value', '?')}")
    except ContextBoxError:
        pass

    # Skills
    try:
        skills = client.list_skills(box_id)
        items = _unwrap_items(skills)
        console.print(f"\n  Skills: {len(items)}")
        for item in items[:5]:
            console.print(f"    {item.get('name', 'unknown')}")
    except ContextBoxError:
        pass

    # Tool Refs
    try:
        tools = client.list_tool_refs(box_id)
        items = _unwrap_items(tools)
        console.print(f"\n  Tool Refs: {len(items)}")
        for item in items[:5]:
            console.print(f"    {item.get('tool_ref', item.get('tool_name', 'unknown'))}")
    except ContextBoxError:
        pass


# =====================================================================
# Task 1.5: arcade ctx push + arcade ctx pull
# =====================================================================


@app.command()
def push(
    urn: str = typer.Argument(..., help="Box URN"),
    files: list[Path] = typer.Argument(..., help="Files to push"),
    replace: bool = typer.Option(False, "--replace", help="Replace existing knowledge"),
) -> None:
    """Push files to a context box as knowledge."""
    client = _get_client()
    box = _resolve_box(client, urn)

    for file_path in files:
        if not file_path.exists():
            console.print(f"Error: File not found: {file_path}", style="bold red")
            raise typer.Exit(code=1)

    uploaded = 0
    for file_path in files:
        try:
            size = _format_size(file_path.stat().st_size)
            console.print(f"  Uploading {file_path.name}... ", end="")
            client.upload_knowledge(box["id"], file_path)
            console.print(f"done ({size})")
            uploaded += 1
        except ContextBoxError as e:
            console.print(f"error: {e.message}", style="bold red")

    console.print(f"Pushed {uploaded} files to {urn}")


@app.command()
def pull(
    urn: str = typer.Argument(..., help="Box URN"),
    output_dir: Path = typer.Option(
        ".", "--output-dir", "-o", help="Directory to download files to"
    ),
) -> None:
    """Pull knowledge files from a context box."""
    client = _get_client()
    box = _resolve_box(client, urn)

    try:
        knowledge = client.list_knowledge(box["id"])
    except ContextBoxError as e:
        console.print(f"Error: {e.message}", style="bold red")
        raise typer.Exit(code=1) from e

    items = knowledge.get("items", [])
    output_dir.mkdir(parents=True, exist_ok=True)

    downloaded = 0
    for item in items:
        uri = item.get("uri", "")
        content = item.get("content", "")
        if not uri:
            continue

        file_path = output_dir / uri
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if content:
            file_path.write_text(content)
            size = _format_size(len(content.encode()))
            console.print(f"  Downloading {uri}... done ({size})")
            downloaded += 1

    console.print(f"Pulled {downloaded} files from {urn} to {output_dir}")


# =====================================================================
# Task 2.1: arcade ctx transition
# =====================================================================

VALID_STATUSES = {"active", "archived", "expired", "attested"}


@app.command()
def transition(
    urn: str = typer.Argument(..., help="Box URN"),
    new_status: str = typer.Argument(..., help="New status: active, archived, expired, attested"),
) -> None:
    """Transition a context box to a new status."""
    if new_status not in VALID_STATUSES:
        console.print(
            f"Error: Invalid status '{new_status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
            style="bold red",
        )
        raise typer.Exit(code=1)

    client = _get_client()
    box = _resolve_box(client, urn)

    try:
        result = client.transition_box(box["id"], new_status)
        console.print(f"Transitioned {urn} to {new_status}")
    except ContextBoxError as e:
        if "already" in e.message.lower():
            console.print(f"Note: Box is already in status '{new_status}'")
        else:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e


# =====================================================================
# Task 2.2: arcade ctx memory
# =====================================================================


@app.command()
def memory(
    urn: str = typer.Argument(..., help="Box URN"),
    action: str = typer.Argument(..., help="Action: list, get, set, delete"),
    key: Optional[str] = typer.Argument(None, help="Memory key"),
    value: Optional[str] = typer.Argument(None, help="Memory value (for set)"),
    format: str = typer.Option("table", "--format", "-f", help="Output format"),
) -> None:
    """Manage context box memory."""
    client = _get_client()
    box = _resolve_box(client, urn)
    box_id = box["id"]

    if action == "list":
        try:
            result = client.list_memory(box_id)
            items = result.get("items", [])
            if format == "json":
                console.print(json.dumps(result))
                return
            if not items:
                console.print("No memory entries found.")
                return
            table = Table()
            table.add_column("KEY")
            table.add_column("VALUE")
            for item in items:
                table.add_row(item.get("key", ""), item.get("value", ""))
            console.print(table)
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    elif action == "get":
        if not key:
            console.print("Error: key is required for get", style="bold red")
            raise typer.Exit(code=1)
        try:
            result = client.get_memory(box_id, key)
            console.print(result.get("value", ""))
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    elif action == "set":
        if not key or value is None:
            console.print("Error: key and value are required for set", style="bold red")
            raise typer.Exit(code=1)
        try:
            client.set_memory(box_id, key, value)
            console.print(f"Set memory key '{key}' = '{value}'")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    elif action == "delete":
        if not key:
            console.print("Error: key is required for delete", style="bold red")
            raise typer.Exit(code=1)
        try:
            client.delete_memory(box_id, key)
            console.print(f"Deleted memory key '{key}'")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    else:
        console.print(f"Error: Unknown action '{action}'. Use list, get, set, or delete.", style="bold red")
        raise typer.Exit(code=1)


# =====================================================================
# Task 2.3: arcade ctx skills
# =====================================================================


@app.command()
def skills(
    urn: str = typer.Argument(..., help="Box URN"),
    action: str = typer.Argument(..., help="Action: list, add, delete"),
    skill_id: Optional[str] = typer.Argument(None, help="Skill ID (for delete)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Skill name"),
    template: Optional[Path] = typer.Option(None, "--template", "-t", help="Template file"),
    required_tools: Optional[str] = typer.Option(
        None, "--required-tools", help="Comma-separated tool list"
    ),
) -> None:
    """Manage context box skills."""
    client = _get_client()
    box = _resolve_box(client, urn)
    box_id = box["id"]

    if action == "list":
        try:
            result = client.list_skills(box_id)
            items = result.get("items", [])
            if not items:
                console.print("No skills found.")
                return
            for item in items:
                tools = item.get("required_tools", [])
                tools_str = f" (requires: {', '.join(tools)})" if tools else ""
                console.print(f"  {item.get('name', 'unknown')}{tools_str}")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    elif action == "add":
        if not name or not template:
            console.print("Error: --name and --template are required for add", style="bold red")
            raise typer.Exit(code=1)
        if not template.exists():
            console.print(f"Error: Template file not found: {template}", style="bold red")
            raise typer.Exit(code=1)
        tmpl_content = template.read_text()
        tools_list = [t.strip() for t in required_tools.split(",")] if required_tools else None
        try:
            result = client.add_skill(box_id, name, tmpl_content, tools_list)
            console.print(f"Added skill '{name}' to {urn}")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    elif action == "delete":
        if not skill_id:
            console.print("Error: skill ID is required for delete", style="bold red")
            raise typer.Exit(code=1)
        try:
            client.delete_skill(box_id, skill_id)
            console.print(f"Deleted skill '{skill_id}'")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    else:
        console.print(f"Error: Unknown action '{action}'. Use list, add, or delete.", style="bold red")
        raise typer.Exit(code=1)


# =====================================================================
# Task 2.4: arcade ctx logs
# =====================================================================


@app.command()
def logs(
    urn: str = typer.Argument(..., help="Box URN"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max log entries"),
) -> None:
    """Show resolution log for a context box."""
    client = _get_client()
    box = _resolve_box(client, urn)

    try:
        result = client.list_resolution_log(box["id"], limit=limit)
    except ContextBoxError as e:
        console.print(f"Error: {e.message}", style="bold red")
        raise typer.Exit(code=1) from e

    items = result.get("items", [])
    total = result.get("total", 0)

    if not items:
        console.print("No log entries found.")
        return

    table = Table()
    table.add_column("TIMESTAMP")
    table.add_column("FACETS REQUESTED")
    table.add_column("FACETS RETURNED")

    for item in items:
        table.add_row(
            item.get("created_at", ""),
            item.get("facets_requested", ""),
            item.get("facets_returned", ""),
        )

    console.print(table)
    console.print(f"\nShowing {len(items)} of {total} log entries")


# =====================================================================
# Task 2.5: arcade ctx template
# =====================================================================


@app.command()
def template(
    action: str = typer.Argument(..., help="Action: list, create, delete"),
    template_id: Optional[str] = typer.Argument(None, help="Template ID (for delete)"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Template name"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Template YAML file"),
) -> None:
    """Manage context box templates."""
    client = _get_client()

    if action == "list":
        try:
            result = client.list_templates()
            items = result.get("items", [])
            if not items:
                console.print("No templates found.")
                return
            for item in items:
                console.print(f"  {item.get('name', 'unknown')} (ID: {item.get('id', '?')})")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    elif action == "create":
        if not name or not file:
            console.print("Error: --name and --file are required for create", style="bold red")
            raise typer.Exit(code=1)
        if not file.exists():
            console.print(f"Error: File not found: {file}", style="bold red")
            raise typer.Exit(code=1)
        content = file.read_text()
        try:
            result = client.create_template(name, content)
            console.print(f"Created template '{name}' (ID: {result.get('id', '?')})")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    elif action == "delete":
        if not template_id:
            console.print("Error: template ID is required for delete", style="bold red")
            raise typer.Exit(code=1)
        try:
            client.delete_template(template_id)
            console.print(f"Deleted template '{template_id}'")
        except ContextBoxError as e:
            console.print(f"Error: {e.message}", style="bold red")
            raise typer.Exit(code=1) from e

    else:
        console.print(f"Error: Unknown action '{action}'. Use list, create, or delete.", style="bold red")
        raise typer.Exit(code=1)
