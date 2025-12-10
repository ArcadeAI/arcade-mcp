import typer
from arcade_core.constants import PROD_COORDINATOR_HOST
from rich.console import Console

from arcade_cli.authn import (
    fetch_organizations,
    fetch_projects,
    select_default_project,
)
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
    """Configure Coordinator connection options for organization commands."""
    coordinator_url = compute_base_url(force_tls, force_no_tls, host, port, default_port=None)
    state["coordinator_url"] = coordinator_url


@app.command("list", help="List organizations you belong to")
def org_list(
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """List all organizations the current user belongs to."""

    from arcade_core.config_model import Config
    from rich.table import Table

    try:
        coordinator_url = state["coordinator_url"]
        orgs = fetch_organizations(coordinator_url)

        if not orgs:
            console.print("No organizations found.", style="yellow")
            return

        # Get current active org
        config = Config.load_from_file()
        active_org_id = config.get_active_org_id()

        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Default", style="green")
        table.add_column("Active", style="bold yellow")

        for org in orgs:
            is_active = "✓" if org.org_id == active_org_id else ""
            is_default = "✓" if org.is_default else ""
            table.add_row(org.name, org.org_id, is_default, is_active)

        console.print(table)
        console.print("\nUse 'arcade org set <org_id>' to switch organizations.\n")

    except ValueError as e:
        handle_cli_error(str(e))
    except Exception as e:
        handle_cli_error("Failed to list organizations", e, debug)


@app.command("set", help="Set the active organization")
def org_set(
    org_id: str = typer.Argument(..., help="Organization ID to set as active"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """Set the active organization and reset project to its default."""

    from arcade_core.config_model import Config, ContextConfig

    try:
        coordinator_url = state["coordinator_url"]

        # Verify org exists and user has access
        orgs = fetch_organizations(coordinator_url)
        target_org = next((o for o in orgs if o.org_id == org_id), None)

        if not target_org:
            console.print(
                f"Organization '{org_id}' not found or you don't have access.", style="bold red"
            )
            console.print("Run 'arcade org list' to see available organizations.", style="dim")
            return

        # Fetch projects and select default
        projects = fetch_projects(coordinator_url, org_id)
        if not projects:
            handle_cli_error(
                f"No projects found in organization '{target_org.name}'. "
                "Contact support@arcade.dev for assistance."
            )
            return

        selected_project = select_default_project(projects)
        if not selected_project:
            handle_cli_error("Could not select a default project.")
            return

        # Update config
        config = Config.load_from_file()
        config.context = ContextConfig(
            org_id=target_org.org_id,
            org_name=target_org.name,
            project_id=selected_project.project_id,
            project_name=selected_project.name,
        )
        config.save_to_file()

        console.print(f"✓ Switched to organization: {target_org.name}", style="bold green")
        console.print(f"  Active project: {selected_project.name}", style="dim")

    except ValueError as e:
        handle_cli_error(str(e))
    except Exception as e:
        handle_cli_error("Failed to set organization", e, debug)
