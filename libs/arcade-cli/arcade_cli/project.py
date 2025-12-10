import typer
from arcade_core.constants import PROD_COORDINATOR_HOST
from rich.console import Console

from arcade_cli.authn import fetch_projects
from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import (
    compute_base_url,
    handle_cli_error,
)

console = Console()


app = TrackedTyper(
    cls=TrackedTyperGroup,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)

state = {
    "coordinator_url": compute_base_url(
        force_tls=False,
        force_no_tls=False,
        host=PROD_COORDINATOR_HOST,
        port=None,
        default_port=None,
    )
}


@app.callback()
def main(
    host: str = typer.Option(
        PROD_COORDINATOR_HOST,
        "--host",
        "-h",
        help="The Arcade Coordinator host.",
    ),
    port: int = typer.Option(
        None,
        "--port",
        "-p",
        help="The port of the Arcade Coordinator host.",
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to Arcade Coordinator.",
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to Arcade Coordinator.",
    ),
) -> None:
    """Configure Coordinator connection options for project commands."""
    coordinator_url = compute_base_url(force_tls, force_no_tls, host, port, default_port=None)
    state["coordinator_url"] = coordinator_url


@app.command("list", help="List projects in the active organization")
def project_list(
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """List all projects in the current active organization."""
    from arcade_core.config_model import Config
    from rich.table import Table

    try:
        config = Config.load_from_file()

        if not config.context:
            console.print("No active organization set. Run 'arcade login' first.", style="bold red")
            return

        coordinator_url = state["coordinator_url"]
        projects = fetch_projects(coordinator_url, config.context.org_id)

        if not projects:
            console.print(
                f"No projects found in organization '{config.context.org_name}'.",
                style="yellow",
            )
            return

        active_project_id = config.get_active_project_id()

        console.print(
            f"\nActive organization: {config.context.org_name}\n"
            "Use 'arcade org list' and 'arcade org set <org_id>' to switch organizations.\n",
        )

        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Default", style="green")
        table.add_column("Active", style="bold yellow")

        for project in projects:
            is_active = "✓" if project.project_id == active_project_id else ""
            is_default = "✓" if project.is_default else ""
            table.add_row(project.name, project.project_id, is_default, is_active)

        console.print(table)
        console.print("\nUse 'arcade project set <project_id>' to switch projects.\n")

    except ValueError as e:
        handle_cli_error(str(e))
    except Exception as e:
        handle_cli_error("Failed to list projects", e, debug)


@app.command("set", help="Set the active project")
def project_set(
    project_id: str = typer.Argument(..., help="Project ID to set as active"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """Set the active project within the current organization."""
    from arcade_core.config_model import Config

    try:
        config = Config.load_from_file()

        if not config.context:
            console.print("No active organization set. Run 'arcade login' first.", style="bold red")
            return

        coordinator_url = state["coordinator_url"]

        # Verify project exists in current org
        projects = fetch_projects(coordinator_url, config.context.org_id)
        target_project = next((p for p in projects if p.project_id == project_id), None)

        if not target_project:
            console.print(
                f"Project '{project_id}' not found in organization '{config.context.org_name}'.",
                style="bold red",
            )
            console.print("Run 'arcade project list' to see available projects.", style="dim")
            return

        # Update config
        config.context.project_id = target_project.project_id
        config.context.project_name = target_project.name
        config.save_to_file()

        console.print(f"✓ Switched to project: {target_project.name}", style="bold green")

    except ValueError as e:
        handle_cli_error(str(e))
    except Exception as e:
        handle_cli_error("Failed to set project", e, debug)
