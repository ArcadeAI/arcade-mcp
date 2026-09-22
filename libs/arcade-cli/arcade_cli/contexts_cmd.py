from __future__ import annotations

import typer
from arcade_core.config_model import Config, NamedContext
from rich.table import Table

from arcade_cli.authn import DEFAULT_OAUTH_TIMEOUT_SECONDS
from arcade_cli.console import console
from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import handle_cli_error

app = TrackedTyper(
    cls=TrackedTyperGroup,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)


def _load_config() -> Config:
    try:
        return Config.load_from_file()
    except FileNotFoundError:
        handle_cli_error("Not logged in. Run 'arcade login' to create a context.")
        raise AssertionError("unreachable")
    except ValueError as e:
        handle_cli_error(str(e))
        raise AssertionError("unreachable")


@app.command("list", help="List saved contexts")
def context_list() -> None:
    config = _load_config()
    names = config.list_context_names()

    if not names:
        console.print("No contexts saved. Run 'arcade login' to create one.", style="yellow")
        return

    table = Table(title="Contexts")
    table.add_column("Name", style="cyan")
    table.add_column("Kind", style="green")
    table.add_column("Engine", style="dim")
    table.add_column("Active", style="bold yellow")

    contexts = config.contexts or {}
    for name in names:
        ctx = contexts[name]
        is_active = "✓" if name == config.active_context else ""
        table.add_row(name, ctx.kind, ctx.engine_url or "-", is_active)

    console.print(table)
    console.print("\nUse 'arcade context set <name>' to switch contexts.\n", style="dim")


@app.command("set", help="Set the active context")
def context_set(
    name: str = typer.Argument(..., help="Name of the context to activate"),
) -> None:
    config = _load_config()

    try:
        config.use_context(name)
    except ValueError as e:
        handle_cli_error(str(e))
        return

    config.save_to_file()
    console.print(f"✓ Switched to context: {name}", style="bold green")


@app.command("use", hidden=True, help="Deprecated alias for 'set'")
def context_use(
    name: str = typer.Argument(..., help="Name of the context to activate"),
) -> None:
    context_set(name)


@app.command("show", help="Show the active context or a named context")
def context_show(
    name: str | None = typer.Argument(None, help="Name of the context to show"),
) -> None:
    config = _load_config()

    target_name = name or config.active_context
    contexts = config.contexts or {}

    if not target_name or target_name not in contexts:
        available = ", ".join(config.list_context_names()) or "none"
        handle_cli_error(f"Context '{target_name}' not found. Available contexts: {available}.")
        return

    ctx: NamedContext = contexts[target_name]
    is_active = target_name == config.active_context

    console.print(f"Context: {target_name}{' (active)' if is_active else ''}", style="bold cyan")
    console.print(f"  Kind: {ctx.kind}")
    console.print(f"  Engine: {ctx.engine_url or '-'}")
    console.print(f"  Coordinator: {ctx.coordinator_url or '-'}")
    console.print(f"  Dashboard: {ctx.dashboard_url or '-'}")
    if ctx.user and ctx.user.email:
        console.print(f"  User: {ctx.user.email}")
    if ctx.context:
        console.print(f"  Organization: {ctx.context.org_name}")
        console.print(f"  Project: {ctx.context.project_name}")


@app.command("delete", help="Delete a saved context")
def context_delete(
    name: str = typer.Argument(..., help="Name of the context to delete"),
) -> None:
    config = _load_config()

    try:
        anything_left = config.remove_context(name)
    except ValueError as e:
        handle_cli_error(str(e))
        return

    config.save_to_file()
    console.print(f"✓ Deleted context: {name}", style="bold green")
    if anything_left:
        console.print(f"Active context is now '{config.active_context}'.", style="dim")
    else:
        console.print(
            "That was the last context. Run 'arcade login' to sign in again.", style="dim"
        )


@app.command("add", help="Log in to an installation and save it as a context")
def context_add(
    url: str = typer.Argument(..., help="Installation URL to log in to"),
    name: str | None = typer.Option(
        None,
        "--context",
        "--context-name",
        help="Name to save the context under (defaults to the installation host).",
    ),
    timeout: int = typer.Option(
        DEFAULT_OAUTH_TIMEOUT_SECONDS,
        "--timeout",
        help="Seconds to wait for the local login callback.",
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """Reach a new installation from the same noun that lists and switches them.

    This is 'arcade login --url' under another name, so that a context has one
    place to be added, switched, inspected and removed.
    """
    from arcade_cli.main import _login_with_url

    _login_with_url(url, name, timeout, debug)
