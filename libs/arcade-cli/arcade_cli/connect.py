"""Connect command — one-command toolkit + gateway setup for Arcade MCP."""

from __future__ import annotations

import json as _json
import logging
import time
from pathlib import Path

import httpx
from arcade_core.constants import PROD_COORDINATOR_HOST, PROD_ENGINE_HOST

from arcade_cli.console import console

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool catalog cache
# ---------------------------------------------------------------------------

_CACHE_DIR = Path.home() / ".arcade" / "cache"
_CACHE_FILE = _CACHE_DIR / "tools.json"
_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_context_key() -> str:
    """Return a string identifying the active org+project (for cache scoping)."""
    try:
        from arcade_cli.utils import get_org_project_context

        org_id, project_id = get_org_project_context()
    except Exception:
        return "unknown"
    else:
        return f"{org_id}:{project_id}"


def _read_cache(debug: bool = False) -> dict[str, list[str]] | None:
    """Return cached toolkit map if the cache file exists, is fresh, and matches the active context."""
    try:
        if not _CACHE_FILE.exists():
            return None
        data = _json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        age = time.time() - data.get("ts", 0)
        if age > _CACHE_TTL_SECONDS:
            if debug:
                console.print(f"  [dim]Cache expired ({age:.0f}s old)[/dim]")
            return None
        # Invalidate if org/project changed
        cached_ctx = data.get("context")
        current_ctx = _get_context_key()
        if cached_ctx and cached_ctx != current_ctx:
            if debug:
                console.print("  [dim]Cache stale (different project context)[/dim]")
            return None
        if debug:
            console.print(f"  [dim]Using cached tool catalog ({age:.0f}s old)[/dim]")
        return data.get("toolkits", {})
    except Exception:
        return None


def _write_cache(toolkits: dict[str, list[str]]) -> None:
    """Persist the toolkit map to disk, scoped to the active org/project."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        _CACHE_FILE.write_text(
            _json.dumps({
                "ts": time.time(),
                "context": _get_context_key(),
                "toolkits": toolkits,
            }),
            encoding="utf-8",
        )
    except Exception:
        logger.debug("Failed to write tool cache", exc_info=True)


# ---------------------------------------------------------------------------
# Well-known toolkit metadata
# ---------------------------------------------------------------------------

TOOLKIT_EXAMPLES: dict[str, list[str]] = {
    "github": [
        "List my open pull requests",
        "Show recent issues in my repo",
        "Create a new issue titled 'Bug: login fails'",
    ],
    "slack": [
        "Send a message to #general saying hello",
        "List my unread Slack messages",
        "Search Slack for messages about deployment",
    ],
    "google": [
        "List my upcoming Google Calendar events",
        "Search my Gmail for emails from Alice",
        "Create a new Google Doc titled 'Meeting Notes'",
    ],
    "linear": [
        "Show my assigned Linear issues",
        "Create a new Linear issue for the API refactor",
    ],
    "notion": [
        "Search my Notion workspace for project plans",
        "Create a new Notion page in my workspace",
    ],
    "jira": [
        "List my open Jira tickets",
        "Create a Jira issue for the backend migration",
    ],
    "spotify": [
        "Play my Discover Weekly playlist",
        "What song is currently playing?",
    ],
    "x": [
        "Post a tweet saying 'Hello from Arcade!'",
        "Search recent tweets about AI tools",
    ],
    "reddit": [
        "Search Reddit for posts about MCP tools",
        "Get the top posts from r/programming",
    ],
    "figma": [
        "List my recent Figma files",
        "Get comments on my latest Figma design",
    ],
    "atlassian": [
        "List my Confluence pages",
        "Search Jira for open bugs",
    ],
    "dropbox": [
        "List files in my Dropbox root folder",
        "Search Dropbox for 'project plan'",
    ],
    "asana": [
        "List my Asana tasks",
        "Create a new Asana task for the launch",
    ],
    "hubspot": [
        "List my recent HubSpot contacts",
        "Search HubSpot deals closing this month",
    ],
    "discord": [
        "Send a message to my Discord server",
        "List channels in my Discord server",
    ],
    "zoom": [
        "List my upcoming Zoom meetings",
        "Create a Zoom meeting for tomorrow at 2pm",
    ],
    "microsoft": [
        "List my recent Outlook emails",
        "Search OneDrive for 'quarterly report'",
    ],
    "pagerduty": [
        "List my on-call schedules",
        "Show recent PagerDuty incidents",
    ],
}

PRESET_BUNDLES: dict[str, list[str]] = {
    "Productivity": ["google", "slack", "notion"],
    "Development": ["github", "linear", "jira"],
    "Communication": ["slack", "google", "x"],
    "Project Management": ["linear", "jira", "notion"],
    "DevOps": ["github", "slack", "linear"],
    "Social": ["x", "slack", "reddit"],
    "Creative": ["spotify", "figma", "notion"],
}


def get_toolkit_examples(toolkits: list[str]) -> list[str]:
    """Return example prompts for the given toolkit names."""
    examples: list[str] = []
    for tk in toolkits:
        tk_lower = tk.lower().replace("arcade-", "").replace("arcade_", "")
        if tk_lower in TOOLKIT_EXAMPLES:
            examples.extend(TOOLKIT_EXAMPLES[tk_lower][:2])
    if not examples:
        examples.append("Ask your AI assistant to use one of the configured tools!")
    return examples


# ---------------------------------------------------------------------------
# Login helper
# ---------------------------------------------------------------------------


def ensure_login(coordinator_url: str | None = None) -> str:
    """Ensure the user is logged in, triggering OAuth if needed.

    Returns the valid access token.
    """
    from arcade_cli.authn import (
        OAuthLoginError,
        check_existing_login,
        get_valid_access_token,
        perform_oauth_login,
        save_credentials_from_whoami,
    )

    resolved_url = coordinator_url or f"https://{PROD_COORDINATOR_HOST}"

    if check_existing_login(suppress_message=True):
        return get_valid_access_token(resolved_url)

    console.print("You need to log in to Arcade first.\n", style="yellow")
    try:
        result = perform_oauth_login(
            resolved_url,
            on_status=lambda msg: console.print(msg, style="dim"),
        )
        save_credentials_from_whoami(result.tokens, result.whoami, resolved_url)
        console.print(f"\nLogged in as {result.email}.", style="bold green")
        return get_valid_access_token(resolved_url)
    except OAuthLoginError as e:
        raise SystemExit(f"Login failed: {e}") from e


# ---------------------------------------------------------------------------
# Arcade API helpers
# ---------------------------------------------------------------------------


def fetch_available_toolkits(
    base_url: str | None = None,
    debug: bool = False,
    skip_cache: bool = False,
) -> dict[str, list[str]]:
    """Fetch tools from the Arcade Engine and group them by toolkit name.

    Results are cached to ``~/.arcade/cache/tools.json`` for 5 minutes so
    repeated invocations (e.g. interactive → allow-list) are instant.

    Returns a dict mapping toolkit names to lists of tool qualified names
    (e.g. ``"Github.ListPRs"``).
    """
    if not skip_cache:
        cached = _read_cache(debug=debug)
        if cached is not None:
            return cached

    from arcadepy import NOT_GIVEN, APIConnectionError

    from arcade_cli.utils import compute_base_url, get_arcade_client

    url = base_url or compute_base_url(False, False, PROD_ENGINE_HOST, None, default_port=None)
    if debug:
        console.print(f"  [dim]Connecting to Arcade Engine at {url}[/dim]")
    client = get_arcade_client(url)

    toolkits: dict[str, list[str]] = {}
    tool_count = 0
    try:
        # limit= is the page size, not a cap — the iterator auto-paginates
        for tool in client.tools.list(toolkit=NOT_GIVEN, limit=1000):
            toolkit_name = getattr(tool.toolkit, "name", None) or "unknown"
            tool_name = tool.name or "unknown"
            # Gateway API requires qualified names: "ToolkitName.ToolName"
            qualified = f"{toolkit_name}.{tool_name}"
            toolkits.setdefault(toolkit_name, []).append(qualified)
            tool_count += 1
            if debug:
                console.print(f"  [dim]  Found tool: {qualified}[/dim]")
    except APIConnectionError:
        console.print(f"Could not connect to Arcade Engine at {url}.", style="bold red")
    except Exception as e:
        if debug:
            console.print(f"  [dim]Error fetching toolkits: {e}[/dim]")
        else:
            logger.debug("Failed to fetch toolkits: %s", e)
        console.print(
            "Could not fetch available toolkits from your account.",
            style="bold red",
        )

    if debug:
        console.print(
            f"  [dim]Fetched {tool_count} tools across {len(toolkits)} toolkits: "
            f"{list(toolkits.keys())}[/dim]"
        )

    if toolkits:
        _write_cache(toolkits)

    return toolkits


def fetch_account_gateways(base_url: str | None = None) -> list[dict]:
    """Fetch MCP gateways (workers of type 'mcp') from the user's account.

    Returns a list of dicts with keys: id, enabled, uri.
    """
    from arcadepy import APIConnectionError

    from arcade_cli.utils import compute_base_url, get_arcade_client

    url = base_url or compute_base_url(False, False, PROD_ENGINE_HOST, None, default_port=None)
    client = get_arcade_client(url)

    gateways: list[dict] = []
    try:
        workers = client.workers.list(limit=100)
        for w in workers.items:
            entry: dict = {
                "id": w.id,
                "enabled": getattr(w, "enabled", True),
                "type": getattr(w, "type", "unknown"),
            }
            mcp = getattr(w, "mcp", None)
            if mcp:
                entry["uri"] = getattr(mcp, "uri", None)
            gateways.append(entry)
    except APIConnectionError:
        console.print(f"Could not connect to Arcade Engine at {url}.", style="bold red")
    except Exception as e:
        logger.debug("Failed to fetch gateways: %s", e)

    return gateways


def list_gateways(
    access_token: str,
    base_url: str | None = None,
    debug: bool = False,
) -> list[dict]:
    """List existing MCP gateways from the user's project.

    Returns a list of gateway dicts (each with ``id``, ``slug``, ``name``,
    ``tool_filter``, etc.).
    """
    from arcade_cli.utils import compute_base_url, get_org_project_context

    url = base_url or compute_base_url(False, False, PROD_ENGINE_HOST, None, default_port=None)
    org_id, project_id = get_org_project_context()

    endpoint = f"{url}/v1/orgs/{org_id}/projects/{project_id}/gateways"

    if debug:
        console.print(f"  [dim]GET {endpoint}[/dim]")

    resp = httpx.get(
        endpoint,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )

    if resp.status_code != 200:
        if debug:
            console.print(f"  [dim]Failed to list gateways: {resp.status_code}[/dim]")
        return []

    data = resp.json()
    return data.get("items", [])


def find_matching_gateway(
    gateways: list[dict],
    tool_allow_list: list[str],
    debug: bool = False,
) -> dict | None:
    """Find an existing gateway whose allow-list is a superset of *tool_allow_list*."""
    needed = set(tool_allow_list)
    for gw in gateways:
        existing = set(gw.get("tool_filter", {}).get("allowed_tools", []))
        if needed <= existing:
            if debug:
                console.print(
                    f"  [dim]Found existing gateway '{gw.get('slug')}' "
                    f"with {len(existing)} tools (covers all {len(needed)} needed)[/dim]"
                )
            return gw
    return None


def create_gateway(
    access_token: str,
    name: str,
    tool_allow_list: list[str],
    auth_type: str = "arcade",
    slug: str | None = None,
    base_url: str | None = None,
    debug: bool = False,
) -> dict:
    """Create a new MCP gateway on Arcade Cloud.

    Args:
        access_token: OAuth access token for the Engine API.
        name: Human-readable gateway name.
        tool_allow_list: Qualified tool names (e.g. ``"Github.CreateIssue"``).
        auth_type: ``"arcade"`` (OAuth, default) or ``"arcade_header"`` (API key).
        slug: Custom slug for the gateway URL. Auto-generated if not provided.
        base_url: Engine API base URL override.
        debug: Print debug output.

    Returns the gateway response dict (with ``slug``, ``id``, ``name``, etc.).
    """
    from arcade_cli.utils import compute_base_url, get_org_project_context

    url = base_url or compute_base_url(False, False, PROD_ENGINE_HOST, None, default_port=None)
    org_id, project_id = get_org_project_context()

    endpoint = f"{url}/v1/orgs/{org_id}/projects/{project_id}/gateways"
    body: dict = {
        "name": name,
        "auth_type": auth_type,
        "tool_filter": {"allowed_tools": tool_allow_list},
    }
    if slug:
        body["slug"] = slug

    if debug:
        console.print(f"  [dim]POST {endpoint}[/dim]")
        console.print(f"  [dim]Body: {body}[/dim]")

    resp = httpx.post(
        endpoint,
        json=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if debug:
        console.print(f"  [dim]Response: {resp.status_code}[/dim]")
        console.print(f"  [dim]{resp.text[:500]}[/dim]")

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create gateway ({resp.status_code}): {resp.text}")

    data = resp.json()

    # The API may return the gateway directly or wrapped in a list/items envelope
    if "slug" in data:
        return data
    if data.get("items"):
        return data["items"][0]
    if "id" in data:
        return data

    if debug:
        console.print(f"  [dim]Unexpected response shape: {list(data.keys())}[/dim]")
    return data


def create_project_api_key(
    access_token: str,
    label: str = "quickstart",
    debug: bool = False,
) -> str:
    """Create a project API key via the Coordinator.

    Calls ``POST /v1/projects/{project_id}/api_keys``.

    Returns the raw API key string (``arc_...``).
    """
    from arcade_cli.utils import get_org_project_context

    _, project_id = get_org_project_context()
    coordinator_url = f"https://{PROD_COORDINATOR_HOST}"
    endpoint = f"{coordinator_url}/v1/projects/{project_id}/api_keys"

    if debug:
        console.print(f"  [dim]POST {endpoint}[/dim]")

    resp = httpx.post(
        endpoint,
        json={"label": label},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    if debug:
        console.print(f"  [dim]Response: {resp.status_code}[/dim]")
        console.print(f"  [dim]{resp.text[:300]}[/dim]")

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to create API key ({resp.status_code}): {resp.text}")

    return resp.json()["api_key"]


# ---------------------------------------------------------------------------
# Interactive selection
# ---------------------------------------------------------------------------


def prompt_toolkit_selection(available: dict[str, list[str]]) -> list[str]:
    """Interactively prompt the user to select toolkits.

    Returns a list of selected toolkit names.
    """
    if not available:
        console.print("No toolkits available in your account.", style="bold red")
        raise SystemExit(1)

    console.print("\n[bold]Available toolkits:[/bold]\n")

    # Show preset bundles first
    bundle_choices: list[tuple[str, list[str]]] = []
    for bundle_name, bundle_tks in PRESET_BUNDLES.items():
        matching = [t for t in bundle_tks if t in available]
        if matching:
            bundle_choices.append((bundle_name, matching))

    sorted_toolkits = sorted(available.keys())

    # Number the options
    idx = 1
    option_map: dict[int, list[str]] = {}

    for bundle_name, bundle_tks in bundle_choices:
        tool_count = sum(len(available.get(t, [])) for t in bundle_tks)
        console.print(
            f"  [bold cyan]{idx}.[/bold cyan] {bundle_name} bundle "
            f"({', '.join(bundle_tks)}) — {tool_count} tools"
        )
        option_map[idx] = bundle_tks
        idx += 1

    if bundle_choices:
        console.print()

    for tk_name in sorted_toolkits:
        tools = available[tk_name]
        console.print(f"  [bold cyan]{idx}.[/bold cyan] {tk_name} — {len(tools)} tools")
        option_map[idx] = [tk_name]
        idx += 1

    console.print(f"\n  [bold cyan]{idx}.[/bold cyan] All available toolkits")
    option_map[idx] = sorted_toolkits

    console.print()
    try:
        raw = input("Select toolkits (comma-separated numbers, e.g. 1,3): ").strip()
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nCancelled.")

    selected: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            choice = int(part)
        except ValueError:
            console.print(f"  Skipping invalid choice: {part}", style="yellow")
            continue
        if choice in option_map:
            for tk in option_map[choice]:
                if tk not in selected:
                    selected.append(tk)
        else:
            console.print(f"  Skipping unknown option: {choice}", style="yellow")

    if not selected:
        console.print("No toolkits selected.", style="bold red")
        raise SystemExit(1)

    return selected


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run_connect(
    client: str,
    toolkits: list[str] | None = None,
    tools: list[str] | None = None,
    gateway: str | None = None,
    all_tools: bool = False,
    use_api_key: bool = False,
    gateway_slug: str | None = None,
    config_path: Path | None = None,
    debug: bool = False,
) -> None:
    """Run the quickstart flow: login → determine mode → configure client.

    Everything is configured as a cloud gateway — no local server required.

    Args:
        toolkits: Whole toolkit names (e.g. ``["github"]``) — adds all tools.
        tools: Individual qualified tool names (e.g. ``["Github.CreateIssue"]``).
        gateway: Existing gateway slug to connect to directly.
    """

    # Step 1: Ensure login
    access_token = ensure_login()

    # Step 2: Determine mode
    if gateway:
        # --- Direct gateway mode (existing gateway) ---
        # Resolve the input: user may pass a name ("opencode") or slug ("pascal_opencode")
        slug = _resolve_gateway_slug(gateway, access_token, debug=debug)
        api_key: str | None = None
        if use_api_key:
            console.print("Creating project API key...", style="dim")
            api_key = create_project_api_key(access_token, label=f"connect-{slug}", debug=debug)
            console.print("  API key created.", style="green")
        _configure_gateway(client, slug, config_path, api_key=api_key, name=gateway)
        return

    # --- Toolkit / tool → gateway mode ---

    # If only --tool is given (no --toolkit, --all, or interactive), skip catalog fetch
    if tools and not toolkits and not all_tools:
        tool_allow_list = list(tools)
        selected_toolkits = sorted({t.split(".")[0] for t in tools})
        console.print(
            f"\nSetting up gateway with {len(tool_allow_list)} individual tool(s): "
            f"[bold]{', '.join(tool_allow_list)}[/bold]\n"
        )
    else:
        selected_toolkits_list: list[str]

        # Fetch the tool catalog once — used for selection and allow-list
        console.print("Fetching tool catalog...", style="dim")
        available = fetch_available_toolkits(debug=debug)

        if toolkits:
            selected_toolkits_list = toolkits
        elif all_tools:
            if not available:
                console.print(
                    "No toolkits found. Make sure you have tools deployed in your Arcade account.",
                    style="bold red",
                )
                raise SystemExit(1)
            selected_toolkits_list = sorted(available.keys())
        else:
            # Interactive mode
            if not available:
                console.print(
                    "No toolkits found in your account. You can specify toolkits manually:\n"
                    "  [bold]arcade connect claude --toolkit github[/bold]",
                    style="yellow",
                )
                raise SystemExit(1)
            selected_toolkits_list = prompt_toolkit_selection(available)

        selected_toolkits = selected_toolkits_list

        console.print(
            f"\nSetting up gateway for toolkits: [bold]{', '.join(selected_toolkits)}[/bold]\n"
        )

        # Build a case-insensitive lookup: "github" -> "Github", etc.
        tk_lower_map: dict[str, str] = {k.lower(): k for k in available}

        if debug:
            console.print(f"  [dim]Available toolkit keys: {list(available.keys())}[/dim]")
            console.print(f"  [dim]Looking for: {selected_toolkits}[/dim]")

        tool_allow_list = []
        for tk in selected_toolkits:
            actual_key = tk_lower_map.get(tk.lower())
            if actual_key:
                tk_tools = available[actual_key]
                tool_allow_list.extend(tk_tools)
                if debug:
                    console.print(
                        f"  [dim]Matched '{tk}' -> '{actual_key}' ({len(tk_tools)} tools)[/dim]"
                    )
            else:
                console.print(f"  [yellow]Warning: No tools found for toolkit '{tk}'.[/yellow]")
                if available:
                    console.print(
                        f"  [yellow]Available toolkits: "
                        f"{', '.join(sorted(available.keys()))}[/yellow]"
                    )

        # Append any individual --tool names
        if tools:
            for t in tools:
                if t not in tool_allow_list:
                    tool_allow_list.append(t)
            if debug:
                console.print(f"  [dim]Added {len(tools)} individual tool(s)[/dim]")

    if not tool_allow_list:
        console.print(
            "\nNo tools to add to the gateway. Deploy toolkits first with "
            "[bold]arcade deploy[/bold].",
            style="bold red",
        )
        raise SystemExit(1)

    # Check if an existing gateway already covers these tools
    console.print("Checking existing gateways...", style="dim")
    existing_gateways = list_gateways(access_token, debug=debug)
    existing = find_matching_gateway(existing_gateways, tool_allow_list, debug=debug)

    if existing:
        slug = existing["slug"]
        console.print(
            f"  Found existing gateway: [bold]{existing.get('name', slug)}[/bold] (slug: {slug})\n",
            style="green",
        )
    else:
        # Create a new gateway
        auth_type = "arcade_header" if use_api_key else "arcade"
        if len(selected_toolkits) == 1:
            gateway_name = selected_toolkits[0].lower()
        else:
            gateway_name = "-".join(sorted({tk.lower() for tk in selected_toolkits}))
        console.print(
            f"Creating gateway '{gateway_name}' with {len(tool_allow_list)} tools "
            f"(auth: {auth_type})...",
            style="dim",
        )

        gw = create_gateway(
            access_token=access_token,
            name=gateway_name,
            tool_allow_list=tool_allow_list,
            auth_type=auth_type,
            slug=gateway_slug,
            debug=debug,
        )

        slug = gw.get("slug", gateway_name)
        if debug:
            console.print(f"  [dim]Gateway response: id={gw.get('id')}, slug={slug}[/dim]")
        console.print(f"  Gateway created: [bold]{slug}[/bold]\n", style="green")

    # For API-key auth, create a project key and include it in the config
    api_key: str | None = None
    if use_api_key:
        console.print("Creating project API key...", style="dim")
        api_key = create_project_api_key(access_token, label=f"connect-{slug}", debug=debug)
        console.print("  API key created.", style="green")

    # Config key: prefer --slug if given, otherwise derive from toolkit names
    if gateway_slug:
        display_name = gateway_slug
    elif len(selected_toolkits) == 1:
        display_name = selected_toolkits[0].lower()
    else:
        display_name = "-".join(sorted({tk.lower() for tk in selected_toolkits}))
    _configure_gateway(client, slug, config_path, api_key=api_key, name=display_name)

    # Print examples
    examples = get_toolkit_examples(selected_toolkits)
    console.print("\nTry asking your AI assistant:", style="bold")
    for ex in examples[:3]:
        console.print(f"   - {ex}", style="dim")


def _resolve_gateway_slug(
    user_input: str,
    access_token: str,
    debug: bool = False,
) -> str:
    """Resolve a gateway name or slug to the actual slug.

    The user may pass a name (``opencode``) or a slug (``pascal_opencode``).
    We look up existing gateways and match by slug first, then by name.
    Falls back to the original input if no match is found.
    """
    gateways = list_gateways(access_token, debug=debug)
    input_lower = user_input.lower()
    for gw in gateways:
        if gw.get("slug", "").lower() == input_lower:
            if debug:
                console.print(f"  [dim]Matched by slug: {gw['slug']}[/dim]")
            return gw["slug"]
    for gw in gateways:
        if gw.get("name", "").lower() == input_lower:
            slug = gw["slug"]
            if debug:
                console.print(f"  [dim]Matched by name '{gw['name']}' -> slug: {slug}[/dim]")
            return slug
    if debug:
        available = [f"{g.get('name')} ({g.get('slug')})" for g in gateways]
        console.print(f"  [dim]No match for '{user_input}', available: {available}[/dim]")
    return user_input


def _configure_gateway(
    client: str,
    slug: str,
    config_path: Path | None,
    api_key: str | None = None,
    name: str | None = None,
) -> None:
    """Configure the MCP client to connect to a gateway by slug.

    *name* is the human-readable label used as the config key (e.g. ``github``).
    Defaults to *slug* if not provided.
    """
    from arcade_cli.configure import configure_client_gateway
    from arcade_cli.utils import compute_base_url

    api_base = compute_base_url(False, False, PROD_ENGINE_HOST, None, default_port=None)
    gateway_url = f"{api_base}/mcp/{slug}"
    server_name = name or slug

    console.print(f"Configuring [bold]{client}[/bold] to connect to gateway: [bold]{slug}[/bold]\n")

    configure_client_gateway(
        client=client,
        server_name=server_name,
        gateway_url=gateway_url,
        auth_token=api_key,
        config_path=config_path,
    )

    console.print("\n[bold green]Setup complete![/bold green]")
    console.print(f"   Gateway URL: {gateway_url}", style="dim")
    if api_key:
        console.print("   Auth: API key (included in config)", style="dim")
    else:
        console.print("   Auth: OAuth (handled by your MCP client)", style="dim")
