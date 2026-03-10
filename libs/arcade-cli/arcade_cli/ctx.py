"""Context Box CLI commands — arcade ctx."""

from __future__ import annotations

import json
import mimetypes
import os
from dataclasses import dataclass, field
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
    files: Optional[list[Path]] = typer.Argument(None, help="Files to push"),
    replace: bool = typer.Option(False, "--replace", help="Replace existing knowledge"),
    auto: bool = typer.Option(
        False, "--auto", help="Auto-detect agent configs and push them"
    ),
) -> None:
    """Push files to a context box as knowledge.

    With --auto, detects .claude/.cursor/.codex directories and pushes their config files.
    """
    client = _get_client()
    box = _resolve_box(client, urn)

    if auto:
        root = Path.cwd().resolve()
        profiles = _detect_agent_profiles(root)
        if not profiles:
            console.print(
                "No agent config detected. Use --auto from a directory with .claude/, .cursor/, .codex/, etc.",
                style="bold yellow",
            )
            raise typer.Exit(code=1)
        agent_names = [p.name for p in profiles]
        console.print(f"Detected agents: {', '.join(agent_names)}")
        auto_files = _collect_files(root, profiles)
        if not auto_files:
            console.print("No matching agent config files found.", style="bold yellow")
            raise typer.Exit(code=1)

        uploaded = 0
        for cf in auto_files:
            if cf.uri_prefix:
                uri = f"{cf.uri_prefix}{cf.path.name}"
            else:
                uri = str(cf.path.relative_to(root))
            content = cf.path.read_text(errors="replace")
            mime = _mime_for_file(cf.path)
            try:
                size = _format_size(len(content.encode()))
                console.print(f"  Uploading {uri}... ", end="")
                client.add_knowledge(box["id"], uri, content, mime)
                console.print(f"done ({size})")
                uploaded += 1
            except ContextBoxError as e:
                console.print(f"error: {e.message}", style="bold red")
        console.print(f"Pushed {uploaded} agent config files to {urn}")
        return

    if not files:
        console.print(
            "Error: Provide files to push, or use --auto to detect agent configs.",
            style="bold red",
        )
        raise typer.Exit(code=1)

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

    items = _unwrap_items(knowledge)
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
# Agent filesystem detection for sync
# =====================================================================

# Max file size to upload as text knowledge (512 KB)
_MAX_TEXT_SIZE = 512 * 1024

# Files/dirs to always skip
_SKIP_NAMES = {
    "__pycache__", "node_modules", ".git", ".DS_Store",
    "*.pyc", "*.pyo", "*.so", "*.dylib",
}

# Text extensions we recognize
_TEXT_EXTENSIONS = {
    ".md", ".txt", ".json", ".yaml", ".yml", ".toml",
    ".py", ".js", ".ts", ".go", ".sh", ".bash",
    ".cfg", ".ini", ".conf", ".env.example",
    ".xml", ".html", ".css", ".sql", ".jsonl",
}


@dataclass
class AgentProfile:
    """Describes an agent's filesystem structure and which files to collect."""

    name: str
    # Marker directories that indicate this agent is present (relative to project root)
    # Only directories count — a CLAUDE.md alone doesn't mean "claude agent is configured"
    markers: list[str]
    # Glob patterns for project-level files to collect (relative to project root)
    project_patterns: list[str]
    # Specific project-level files to always include if they exist
    project_files: list[str] = field(default_factory=list)
    # Home-level directory name (e.g., ".claude" → ~/.claude)
    home_dir: str = ""
    # Glob patterns for home-level files (relative to ~/.agent/projects/<encoded-path>/)
    home_project_patterns: list[str] = field(default_factory=list)
    # Glob patterns for home-level global files (relative to ~/.agent/)
    home_global_patterns: list[str] = field(default_factory=list)


def _encode_project_path(root: Path) -> str:
    """Encode a project path the way Claude Code does: replace / with - and strip leading -."""
    encoded = str(root).replace("/", "-")
    return encoded.lstrip("-")


AGENT_PROFILES: list[AgentProfile] = [
    AgentProfile(
        name="claude",
        markers=[".claude"],
        project_patterns=[
            # Project-level .claude/ config (committed to git)
            ".claude/settings.json",
            ".claude/settings.local.json",
            ".claude/skills/**/*.md",
            ".claude/format-hook.sh",
        ],
        project_files=["CLAUDE.md", "AGENTS.md"],
        home_dir=".claude",
        home_project_patterns=[
            # ~/.claude/projects/{encoded}/memory/ — persistent cross-session memory
            "memory/*.md",
            # Session index — lists all sessions with summaries
            "sessions-index.json",
        ],
        home_global_patterns=[
            # ~/.claude/settings.json — global settings
            "settings.json",
            # ~/.claude/plugins/**/SKILL.md — installed plugin skills
            "plugins/**/SKILL.md",
            "plugins/**/plugin.json",
            # ~/.claude/plugins/**/agents/*.md — subagent definitions
            "plugins/**/agents/*.md",
        ],
    ),
    AgentProfile(
        name="cursor",
        markers=[".cursor"],
        project_patterns=[
            # Project-level .cursor/ config
            ".cursor/mcp.json",
            ".cursor/rules/**/*.md",
        ],
        project_files=[".cursorrules"],
        home_dir=".cursor",
        home_project_patterns=[
            # ~/.cursor/projects/{encoded}/mcps/ — project-specific MCP configs
            "mcps/**/*.json",
        ],
        home_global_patterns=[
            # ~/.cursor/mcp.json — global MCP server connections
            "mcp.json",
            # ~/.cursor/skills/{name}/SKILL.md — user-installed skills
            "skills/**/SKILL.md",
        ],
    ),
    AgentProfile(
        name="codex",
        markers=[".codex"],
        project_patterns=[
            ".codex/**/*.md",
            ".codex/**/*.json",
        ],
        project_files=["AGENTS.md"],
    ),
]


def _detect_agent_profiles(root: Path) -> list[AgentProfile]:
    """Detect which agent profiles are present in the given directory.

    Only detects based on directory markers (e.g., .claude/, .cursor/),
    not standalone files like CLAUDE.md.
    """
    found: list[AgentProfile] = []
    for profile in AGENT_PROFILES:
        for marker in profile.markers:
            marker_path = root / marker
            if marker_path.is_dir():
                found.append(profile)
                break
    return found


def _is_text_file(path: Path) -> bool:
    """Check if a file looks like a text file we should upload."""
    if path.stat().st_size > _MAX_TEXT_SIZE:
        return False
    if path.name in _SKIP_NAMES:
        return False
    ext = path.suffix.lower()
    if ext in _TEXT_EXTENSIONS:
        return True
    if path.name in {
        "CLAUDE.md", "AGENTS.md", ".cursorrules",
        "settings.json", "settings.local.json", "mcp.json",
        "openclaw.json", "cadecoder.toml", "mcp_servers.json",
        "format-hook.sh", "sessions-index.json",
    }:
        return True
    mime, _ = mimetypes.guess_type(str(path))
    return bool(mime and mime.startswith("text/"))


@dataclass
class CollectedFile:
    """A file collected for sync, with its source context."""

    path: Path
    # URI prefix for organizing in the box (e.g., "project/", "home/global/", "home/project/")
    uri_prefix: str


def _collect_files(
    root: Path,
    profiles: list[AgentProfile],
    include_home: bool = True,
) -> list[CollectedFile]:
    """Collect files matching the detected agent profiles.

    Scans both the project directory and home-level agent directories.
    """
    collected: dict[str, CollectedFile] = {}  # uri → CollectedFile (dedup by uri)

    for profile in profiles:
        # 1. Project-level specific files
        for specific in profile.project_files:
            path = root / specific
            if path.is_file() and _is_text_file(path):
                uri = str(path.relative_to(root))
                collected[uri] = CollectedFile(path, "")

        # 2. Project-level glob patterns
        for pattern in profile.project_patterns:
            for match in root.glob(pattern):
                if match.is_file() and _is_text_file(match):
                    uri = str(match.relative_to(root))
                    collected[uri] = CollectedFile(match, "")

        # 3. Home-level files (if enabled and home_dir is set)
        if include_home and profile.home_dir:
            home_agent_dir = Path.home() / profile.home_dir

            # Home global files (e.g., ~/.claude/settings.json)
            for pattern in profile.home_global_patterns:
                for match in home_agent_dir.glob(pattern):
                    if match.is_file() and _is_text_file(match):
                        rel = match.relative_to(home_agent_dir)
                        uri = f"~{profile.home_dir}/{rel}"
                        collected[uri] = CollectedFile(match, f"~{profile.home_dir}/")

            # Home project-specific files (e.g., ~/.claude/projects/<encoded>/memory/)
            if profile.home_project_patterns:
                encoded_path = _encode_project_path(root)
                project_data_dir = home_agent_dir / "projects" / encoded_path
                if project_data_dir.is_dir():
                    for pattern in profile.home_project_patterns:
                        for match in project_data_dir.glob(pattern):
                            if match.is_file() and _is_text_file(match):
                                rel = match.relative_to(project_data_dir)
                                uri = f"~{profile.home_dir}/project/{rel}"
                                collected[uri] = CollectedFile(
                                    match, f"~{profile.home_dir}/project/"
                                )

    return sorted(collected.values(), key=lambda cf: cf.path)


def _get_default_owner() -> str:
    """Get default owner name for box creation."""
    return os.environ.get("USER", os.environ.get("USERNAME", "default"))


def _mime_for_file(path: Path) -> str:
    """Determine MIME type for a file."""
    ext = path.suffix.lower()
    if ext == ".md":
        return "text/markdown"
    if ext == ".json":
        return "application/json"
    if ext in {".yaml", ".yml"}:
        return "text/yaml"
    if ext == ".toml":
        return "text/toml"
    if ext == ".jsonl":
        return "application/jsonl"
    return "text/plain"


@app.command()
def sync(
    urn: Optional[str] = typer.Argument(
        None, help="Box URN (auto-creates if not provided)"
    ),
    root: Path = typer.Option(
        ".", "--root", "-r", help="Project root directory to scan"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-n", help="Show what would be uploaded without uploading"
    ),
    name: Optional[str] = typer.Option(
        None, "--name", help="Box name for auto-create (default: owner/dirname)"
    ),
    no_home: bool = typer.Option(
        False, "--no-home", help="Skip scanning home-level agent directories"
    ),
) -> None:
    """Sync agent config files from the current project to a context box.

    Scans both project-level config (.claude/, .cursor/, .codex/) and
    home-level agent data (~/.claude/projects/<project>/memory/, ~/.cursor/mcp.json, etc.).

    If no URN is provided, creates a new box named owner/dirname.
    """
    root = root.resolve()

    # Detect agent profiles
    profiles = _detect_agent_profiles(root)
    if not profiles:
        console.print(
            "No agent config detected. Looked for: .claude/, .cursor/, .codex/",
            style="bold yellow",
        )
        raise typer.Exit(code=1)

    agent_names = [p.name for p in profiles]
    console.print(f"Detected agents: {', '.join(agent_names)}")

    # Collect files from project + home
    files = _collect_files(root, profiles, include_home=not no_home)
    if not files:
        console.print("No matching files found to sync.", style="bold yellow")
        raise typer.Exit(code=1)

    console.print(f"Found {len(files)} files to sync:")
    for cf in files:
        # Show a friendly label
        if cf.uri_prefix.startswith("~"):
            label = f"{cf.uri_prefix}{cf.path.name}"
        else:
            try:
                label = str(cf.path.relative_to(root))
            except ValueError:
                label = str(cf.path)
        size = _format_size(cf.path.stat().st_size)
        console.print(f"  {label} ({size})")

    if dry_run:
        console.print("\nDry run — no changes made.")
        return

    client = _get_client()

    # Resolve or create box
    if urn:
        box = _resolve_box(client, urn)
        console.print(f"\nSyncing to: {box.get('urn', urn)}")
    else:
        owner = _get_default_owner()
        box_name = name or f"{owner}/{root.name}"
        # Ensure owner/name format
        if "/" not in box_name:
            box_name = f"{owner}/{box_name}"
        # Try to resolve first
        try:
            box = client.resolve_urn(f"urn:arcade:ctx:{box_name}")
            console.print(f"\nFound existing box: {box.get('urn')}")
        except ContextBoxError:
            console.print(f"\nCreating new box: {box_name}")
            desc = f"Agent config synced from {root.name} ({', '.join(agent_names)})"
            try:
                box = client.create_box(box_name, desc)
                console.print(f"  Created: {box.get('urn')}")
            except ContextBoxError as e:
                console.print(f"Error creating box: {e.message}", style="bold red")
                raise typer.Exit(code=1) from e

    box_id = box["id"]

    # Upload each file as knowledge
    uploaded = 0
    for cf in files:
        # Build URI: use prefix for home files, relative path for project files
        if cf.uri_prefix:
            try:
                parent_dir = cf.path.parent
                # For home project files, get relative to the project data dir
                rel_name = cf.path.name
                if cf.uri_prefix.endswith("/project/"):
                    # e.g. ~/.claude/project/memory/MEMORY.md
                    # Find the encoded project dir and get relative from there
                    parts = cf.path.parts
                    # Find "projects" in path and take everything after encoded-path
                    for i, part in enumerate(parts):
                        if part == "projects" and i + 2 < len(parts):
                            rel_name = str(Path(*parts[i + 2 :]))
                            break
                    uri = f"{cf.uri_prefix}{rel_name}"
                else:
                    # Home global: relative to agent home dir
                    for profile in profiles:
                        if profile.home_dir and cf.uri_prefix.startswith(
                            f"~{profile.home_dir}"
                        ):
                            home_dir = Path.home() / profile.home_dir
                            try:
                                rel = cf.path.relative_to(home_dir)
                                uri = f"~{profile.home_dir}/{rel}"
                            except ValueError:
                                uri = f"{cf.uri_prefix}{cf.path.name}"
                            break
                    else:
                        uri = f"{cf.uri_prefix}{cf.path.name}"
            except Exception:
                uri = f"{cf.uri_prefix}{cf.path.name}"
        else:
            uri = str(cf.path.relative_to(root))

        content = cf.path.read_text(errors="replace")
        mime = _mime_for_file(cf.path)

        try:
            size = _format_size(len(content.encode()))
            console.print(f"  Uploading {uri}... ", end="")
            client.add_knowledge(box_id, uri, content, mime)
            console.print(f"done ({size})")
            uploaded += 1
        except ContextBoxError as e:
            console.print(f"error: {e.message}", style="bold red")

    console.print(f"\nSynced {uploaded}/{len(files)} files to {box.get('urn', box_id)}")


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
    action: str = typer.Argument(..., help="Action: list, get, set, delete"),
    urn: str = typer.Argument(..., help="Box URN"),
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
            items = _unwrap_items(result)
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
    action: str = typer.Argument(..., help="Action: list, add, delete"),
    urn: str = typer.Argument(..., help="Box URN"),
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
            items = _unwrap_items(result)
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

    items = _unwrap_items(result)
    total = result.get("total", len(items)) if isinstance(result, dict) else len(items)

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
            items = _unwrap_items(result)
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
