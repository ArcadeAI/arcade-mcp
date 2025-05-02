import re
import shutil
from datetime import datetime
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Optional

import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console

from arcade.cli.deployment import (
    create_demo_deployment,
)

console = Console()

# Retrieve the installed version of arcade-ai
try:
    ARCADE_VERSION = get_version("arcade-ai")
except Exception as e:
    console.print(f"[red]Failed to get arcade-ai version: {e}[/red]")
    ARCADE_VERSION = "0.0.0"  # Default version if unable to fetch

TEMPLATE_IGNORE_PATTERN = re.compile(
    r"(__pycache__|\.DS_Store|Thumbs\.db|\.git|\.svn|\.hg|\.vscode|\.idea|build|dist|.*\.egg-info|.*\.pyc|.*\.pyo)$"
)


def ask_question(question: str, default: Optional[str] = None) -> str:
    """
    Ask a question via input() and return the answer.
    """
    answer = typer.prompt(question, default=default)
    if not answer and default:
        return default
    return str(answer)


def render_template(env: Environment, template_string: str, context: dict) -> str:
    """Render a template string with the given variables."""
    template = env.from_string(template_string)
    return template.render(context)


def write_template(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content, encoding="utf-8")


def create_package(env: Environment, template_path: Path, output_path: Path, context: dict) -> None:
    """Recursively create a new toolkit directory structure from jinja2 templates."""
    if TEMPLATE_IGNORE_PATTERN.match(template_path.name):
        return

    try:
        if template_path.is_dir():
            folder_name = render_template(env, template_path.name, context)
            new_dir_path = output_path / folder_name
            new_dir_path.mkdir(parents=True, exist_ok=True)

            for item in template_path.iterdir():
                create_package(env, item, new_dir_path, context)

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
        shutil.rmtree(toolkit_path)


def create_new_toolkit(output_directory: str) -> None:
    """Create a new toolkit from a template with user input."""
    toolkit_directory = Path(output_directory)
    while True:
        name = ask_question("Name of the new toolkit?")
        package_name = name if name.startswith("arcade_") else f"arcade_{name}"

        # Check for illegal characters in the toolkit name
        if re.match(r"^[\w_]+$", package_name):
            toolkit_name = package_name.replace("arcade_", "", 1)

            if (toolkit_directory / toolkit_name).exists():
                console.print(f"[red]Toolkit {toolkit_name} already exists.[/red]")
                continue
            break
        else:
            console.print(
                "[red]Toolkit name contains illegal characters. "
                "Only alphanumeric characters and underscores are allowed. "
                "Please try again.[/red]"
            )

    toolkit_description = ask_question("Description of the toolkit?")
    toolkit_author_name = ask_question("Github owner username?")
    toolkit_author_email = ask_question("Author's email?")

    context = {
        "package_name": package_name,
        "toolkit_name": toolkit_name,
        "toolkit_description": toolkit_description,
        "toolkit_author_name": toolkit_author_name,
        "toolkit_author_email": toolkit_author_email,
        "arcade_version": f"^{ARCADE_VERSION}",
        "creation_year": datetime.now().year,
    }
    template_directory = Path(__file__).parent.parent / "templates" / "{{ toolkit_name }}"

    env = Environment(
        loader=FileSystemLoader(str(template_directory)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    try:
        create_package(env, template_directory, toolkit_directory, context)
        create_deployment(toolkit_directory, toolkit_name)
    except Exception:
        remove_toolkit(toolkit_directory, toolkit_name)
        raise


def create_deployment(toolkit_directory: Path, toolkit_name: str) -> None:
    worker_toml = toolkit_directory / "worker.toml"
    if not worker_toml.exists():
        create_demo_deployment(worker_toml, toolkit_name)
    else:
        pass
        # Disabled pending bug fix
        # update_deployment_with_local_packages(worker_toml, toolkit_name)
