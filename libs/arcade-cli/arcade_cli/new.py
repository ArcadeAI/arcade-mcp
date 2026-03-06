import re
import shutil
from datetime import datetime
from importlib.metadata import version as get_version
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from arcade_cli.console import console
from arcade_cli.templates import get_full_template_directory, get_minimal_template_directory

# Retrieve the installed version of arcade-mcp
try:
    ARCADE_MCP_MIN_VERSION = get_version("arcade-mcp")
    ARCADE_MCP_MAX_VERSION = str(int(ARCADE_MCP_MIN_VERSION.split(".")[0]) + 1) + ".0.0"
except Exception as e:
    console.print(f"[red]Failed to get arcade-mcp version: {e}[/red]")
    ARCADE_MCP_MIN_VERSION = "1.10.0"  # Default version if unable to fetch
    ARCADE_MCP_MAX_VERSION = "2.0.0"

ARCADE_MCP_SERVER_MIN_VERSION = "1.17.0"
ARCADE_MCP_SERVER_MAX_VERSION = "2.0.0"


def render_template(env: Environment, template_string: str, context: dict) -> str:
    """Render a template string with the given variables."""
    template = env.from_string(template_string)
    return template.render(context)


def write_template(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content, encoding="utf-8")


def create_ignore_pattern(include_evals: bool) -> re.Pattern[str]:
    """Create an ignore pattern based on user preferences."""
    patterns = [
        "__pycache__",
        r"\.DS_Store",
        r"Thumbs\.db",
        r"\.git",
        r"\.svn",
        r"\.hg",
        r"\.vscode",
        r"\.idea",
        "build",
        "dist",
        r".*\.egg-info",
        r".*\.pyc",
        r".*\.pyo",
    ]

    if not include_evals:
        patterns.append("evals")

    return re.compile(f"({'|'.join(patterns)})$")


def create_package(
    env: Environment,
    template_path: Path,
    output_path: Path,
    context: dict,
    ignore_pattern: re.Pattern[str],
) -> None:
    """Recursively create a new toolkit directory structure from jinja2 templates."""
    if ignore_pattern.match(template_path.name):
        return

    try:
        if template_path.is_dir():
            folder_name = render_template(env, template_path.name, context)
            new_dir_path = output_path / folder_name
            new_dir_path.mkdir(parents=True, exist_ok=True)

            for item in template_path.iterdir():
                create_package(env, item, new_dir_path, context, ignore_pattern)

        else:
            # Render the file name
            file_name = render_template(env, template_path.name, context)
            with open(template_path, encoding="utf-8") as f:
                content = f.read()
            # Render the file content
            content = render_template(env, content, context)

            write_template(output_path / file_name, content)
    except Exception as e:
        console.print(f"[red]Failed to create package: {e}[/red]")
        raise


def remove_toolkit(toolkit_directory: Path, toolkit_name: str) -> None:
    """Teardown logic for when creating a new toolkit fails."""
    toolkit_path = toolkit_directory / toolkit_name
    if toolkit_path.exists():
        try:
            shutil.rmtree(toolkit_path)
        except (PermissionError, OSError) as e:
            # On Windows, files may still be locked by another process.
            console.print(f"[yellow]Warning: Could not fully remove '{toolkit_path}': {e}[/yellow]")


def create_new_toolkit(output_directory: str, toolkit_name: str) -> None:
    """Create a new toolkit from a template with user input."""
    toolkit_directory = Path(output_directory)

    # Check for illegal characters in the toolkit name
    if re.match(r"^[a-z0-9_]+$", toolkit_name):
        if (toolkit_directory / toolkit_name).exists():
            console.print(f"[red]Server '{toolkit_name}' already exists.[/red]")
            exit(1)
    else:
        console.print(
            "[red]Server name contains illegal characters. "
            "Only lowercase alphanumeric characters and underscores are allowed. "
            "Please try again.[/red]"
        )
        exit(1)

    toolkit_name_title = toolkit_name.replace("_", " ").title()
    toolkit_name_hyphenated = toolkit_name.replace("_", "-")
    toolkit_description = f"Arcade.dev tools for interacting with {toolkit_name_title}"

    context = {
        "package_name": "arcade_" + toolkit_name,
        "toolkit_name": toolkit_name,
        "toolkit_name_title": toolkit_name_title,
        "toolkit_name_hyphenated": toolkit_name_hyphenated,
        "toolkit_description": toolkit_description,
        "arcade_mcp_server_min_version": ARCADE_MCP_SERVER_MIN_VERSION,
        "arcade_mcp_server_max_version": ARCADE_MCP_SERVER_MAX_VERSION,
        "arcade_mcp_min_version": ARCADE_MCP_MIN_VERSION,
        "arcade_mcp_max_version": ARCADE_MCP_MAX_VERSION,
        "creation_year": datetime.now().year,
    }

    template_directory = get_full_template_directory() / "{{ toolkit_name }}"

    env = Environment(
        loader=FileSystemLoader(str(template_directory)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )

    ignore_pattern = create_ignore_pattern(include_evals=True)

    try:
        create_package(env, template_directory, toolkit_directory, context, ignore_pattern)
        console.print(
            f"[green]Toolkit '{toolkit_name}' created successfully at '{toolkit_directory}'.[/green]"
        )
        console.print("\nNext steps:", style="bold")
        console.print(f"  1. cd {toolkit_directory / toolkit_name}")
        console.print("  2. make install")
        console.print("  3. make dev          # serve with MCP and worker endpoints")
        console.print("  4. make test         # run tests")
        console.print("  5. make lint         # run linting")
        console.print("")
    except Exception:
        remove_toolkit(toolkit_directory, toolkit_name)
        raise


def create_new_toolkit_minimal(output_directory: str, toolkit_name: str) -> None:
    """Create a new toolkit from a template with user input."""
    toolkit_directory = Path(output_directory)

    # Check for illegal characters in the toolkit name
    if re.match(r"^[a-z0-9_]+$", toolkit_name):
        if (toolkit_directory / toolkit_name).exists():
            raise FileExistsError(
                f"Server with name '{toolkit_name}' already exists at '{toolkit_directory / toolkit_name}'"
            )
    else:
        raise ValueError(
            f"Server name '{toolkit_name}' contains illegal characters. "
            "Only lowercase alphanumeric characters and underscores are allowed. "
            "Please try again."
        )

    context = {
        "toolkit_name": toolkit_name,
        "arcade_mcp_min_version": ARCADE_MCP_MIN_VERSION,
        "arcade_mcp_max_version": ARCADE_MCP_MAX_VERSION,
        "arcade_mcp_server_min_version": ARCADE_MCP_SERVER_MIN_VERSION,
        "arcade_mcp_server_max_version": ARCADE_MCP_SERVER_MAX_VERSION,
    }
    template_directory = get_minimal_template_directory() / "{{ toolkit_name }}"

    env = Environment(
        loader=FileSystemLoader(str(template_directory)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )

    ignore_pattern = create_ignore_pattern(False)

    try:
        create_package(env, template_directory, toolkit_directory, context, ignore_pattern)
        console.print("")
        console.print(
            f"[green]Server '{toolkit_name}' created successfully at '{toolkit_directory}'.[/green]"
        )
        server_dir = toolkit_directory / toolkit_name / "src" / toolkit_name
        console.print("\nNext steps:", style="bold")
        console.print(f"  1. cd {server_dir}")
        console.print("")
        console.print("  2. Run the server (choose one transport):", style="dim")
        console.print("     - stdio: uv run server.py")
        console.print("     - http:  uv run server.py --transport http --port 8000")
        console.print("")
    except Exception:
        remove_toolkit(toolkit_directory, toolkit_name)
        raise
