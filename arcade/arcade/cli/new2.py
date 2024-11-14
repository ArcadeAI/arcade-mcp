import re
from pathlib import Path
from typing import Optional

import typer
from jinja2 import Environment, FileSystemLoader, select_autoescape
from rich.console import Console

console = Console()


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
    path.write_text(content)


def create_structure(
    env: Environment, template_path: Path, output_path: Path, context: dict
) -> None:
    """Recursively create a new toolkit directory structure from jinja2 templates."""
    if template_path.is_dir():
        folder_name = render_template(env, template_path.name, context)
        new_dir_path = output_path / folder_name
        new_dir_path.mkdir(parents=True, exist_ok=True)

        for item in template_path.iterdir():
            create_structure(env, item, new_dir_path, context)

    else:
        # Render the file name
        file_name = render_template(env, template_path.name, context)
        with open(template_path) as f:
            content = f.read()
        # Render the file content
        content = render_template(env, content, context)

        write_template(output_path / file_name, content)


def create_toolkit_template(toolkit_directory: str) -> None:
    """Create a new toolkit template."""
    while True:
        name = ask_question("Name of the new toolkit?")
        package_name = name if name.startswith("arcade_") else f"arcade_{name}"

        # Check for illegal characters in the toolkit name
        if re.match(r"^[\w_]+$", package_name):
            break
        else:
            console.print(
                "[red]Toolkit name contains illegal characters. "
                "Only alphanumeric characters and underscores are allowed. "
                "Please try again.[/red]"
            )

    toolkit_name = package_name.replace("arcade_", "")
    toolkit_description = ask_question("Description of the toolkit?")
    toolkit_author_name = ask_question("Author's name?")
    toolkit_author_email = ask_question("Author's email?")

    context = {
        "package_name": package_name,
        "toolkit_name": toolkit_name,
        "toolkit_description": toolkit_description,
        "toolkit_author_name": toolkit_author_name,
        "toolkit_author_email": toolkit_author_email,
    }
    template_directory = Path(__file__).parent.parent / "templates" / "{{ toolkit_name }}"

    env = Environment(
        loader=FileSystemLoader(str(template_directory)),
        autoescape=select_autoescape(["html", "xml"]),
    )

    toolkit_directory = Path(toolkit_directory)
    create_structure(env, template_directory, toolkit_directory, context)
