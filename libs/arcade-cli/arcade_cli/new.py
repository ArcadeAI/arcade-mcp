import re
import shutil
from datetime import datetime
from importlib.metadata import version as get_version
from pathlib import Path
from typing import Optional

import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console

from arcade_cli.deployment import (
    create_demo_deployment,
)

console = Console()

# Retrieve the installed version of arcade-ai
try:
    ARCADE_AI_MIN_VERSION = get_version("arcade-ai")
    ARCADE_AI_MAX_VERSION = str(int(ARCADE_AI_MIN_VERSION.split(".")[0]) + 1) + ".0.0"
except Exception as e:
    console.print(f"[red]Failed to get arcade-ai version: {e}[/red]")
    ARCADE_AI_MIN_VERSION = "2.0.0"  # Default version if unable to fetch
    ARCADE_AI_MAX_VERSION = "3.0.0"

ARCADE_TDK_MIN_VERSION = "2.0.0"
ARCADE_TDK_MAX_VERSION = "3.0.0"
ARCADE_SERVE_MIN_VERSION = "2.0.0"
ARCADE_SERVE_MAX_VERSION = "3.0.0"


def ask_question(question: str, default: Optional[str] = None) -> str:
    """
    Ask a question via input() and return the answer.
    """
    answer = typer.prompt(question, default=default, show_default=False)
    if not answer and default:
        return default
    return str(answer)


def ask_yes_no_question(question: str, default: bool = True) -> bool:
    """
    Ask a yes/no question via input() and return the bool answer.
    """
    default_str = "Y/n" if default else "y/N"
    answer = typer.prompt(
        f"{question} ({default_str})", default="y" if default else "n", show_default=False
    )
    return answer.lower() in [
        "y",
        "y/",
        "yes",
        "true",
        "1",
        "ye",
        "yes",
        "yeah",
        "yep",
        "sure",
        "ok",
        "yup",
    ]


def render_template(env: Environment, template_string: str, context: dict) -> str:
    """Render a template string with the given variables."""
    template = env.from_string(template_string)
    return template.render(context)


def write_template(path: Path, content: str) -> None:
    """Write content to a file."""
    path.write_text(content, encoding="utf-8")


def create_ignore_pattern(include_evals: bool, community_toolkit: bool) -> re.Pattern[str]:
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

    if not community_toolkit:
        patterns.extend([".ruff.toml", ".pre-commit-config.yaml", "README.md"])

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
        shutil.rmtree(toolkit_path)


def create_new_toolkit(output_directory: str, toolkit_name: str) -> None:
    """Create a new toolkit from a template with user input."""
    toolkit_directory = Path(output_directory)

    package_name = toolkit_name if toolkit_name.startswith("arcade_") else f"arcade_{toolkit_name}"

    # Check for illegal characters in the toolkit name
    if re.match(r"^[a-z0-9_]+$", package_name):
        toolkit_name = package_name.replace("arcade_", "", 1)

        if (toolkit_directory / toolkit_name).exists():
            console.print(f"[red]Toolkit '{toolkit_name}' already exists.[/red]")
            exit(1)
    else:
        console.print(
            "[red]Toolkit name contains illegal characters. "
            "Only lowercase alphanumeric characters and underscores are allowed. "
            "Please try again.[/red]"
        )
        exit(1)

    toolkit_description = ask_question("Describe what your toolkit will do (optional)", default="")
    toolkit_author_name = ask_question("Your GitHub username (optional)", default="")
    while True:
        toolkit_author_email = ask_question("Your email (optional)", default="")
        if toolkit_author_email == "" or re.match(r"[^@ ]+@[^@ ]+\.[^@ ]+", toolkit_author_email):
            break
        console.print(
            "[red]Invalid email format. Please enter a valid email address or leave it empty.[/red]"
        )
    include_evals = ask_yes_no_question(
        "Do you want an evals directory created for you?", default=True
    )

    cwd = Path.cwd()
    # TODO: this detection mechanism works only for people that didn't change the
    # name of the repo, a better detection method is required here
    community_toolkit = False
    if cwd.name == "toolkits" and cwd.parent.name == "arcade-ai":
        community_toolkit = ask_yes_no_question(
            "Is your toolkit a community contribution (to be merged into Arcade's `arcade-ai` repo)?",
            default=False,  # False for now to keep the default behavior
        )

    context = {
        "package_name": package_name,
        "toolkit_name": toolkit_name,
        "toolkit_description": toolkit_description,
        "toolkit_author_name": toolkit_author_name,
        "toolkit_author_email": toolkit_author_email,
        "arcade_tdk_min_version": ARCADE_TDK_MIN_VERSION,
        "arcade_tdk_max_version": ARCADE_TDK_MAX_VERSION,
        "arcade_serve_min_version": ARCADE_SERVE_MIN_VERSION,
        "arcade_serve_max_version": ARCADE_SERVE_MAX_VERSION,
        "arcade_ai_min_version": ARCADE_AI_MIN_VERSION,
        "arcade_ai_max_version": ARCADE_AI_MAX_VERSION,
        "creation_year": datetime.now().year,
        "community_toolkit": community_toolkit,
    }
    template_directory = Path(__file__).parent / "templates" / "{{ toolkit_name }}"

    env = Environment(
        loader=FileSystemLoader(str(template_directory)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    # Create dynamic ignore pattern based on user preferences
    ignore_pattern = create_ignore_pattern(include_evals, community_toolkit)

    try:
        create_package(env, template_directory, toolkit_directory, context, ignore_pattern)
        console.print(
            f"[green]Toolkit '{toolkit_name}' created successfully at '{toolkit_directory}'.[/green]"
        )
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
