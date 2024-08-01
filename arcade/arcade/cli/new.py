import os
import re
from textwrap import dedent
from typing import Optional

import typer
from rich.console import Console

from arcade.core.version import VERSION

console = Console()

DEFAULT_VERSIONS = {
    "python": "^3.10",
    "arcade-ai": f"^{VERSION}",
    "pytest": "^7.4.0",
}


def ask_question(question: str, default: Optional[str] = None) -> str:
    """
    Ask a question via input() and return the answer.
    """
    if default:
        question = f"{question} [{default}]"
    answer = typer.prompt(question)
    if not answer and default:
        return default
    return str(answer)


def create_directory(path: str) -> None:
    """
    Create a directory if it doesn't exist.
    """
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        console.print(f"[red]Failed to create directory {path}: {e}[/red]")


def create_file(path: str, content: str) -> None:
    """
    Create a file with the given content.
    """
    try:
        with open(path, "w") as f:
            f.write(content)
    except Exception as e:
        console.print(f"[red]Failed to create file {path}: {e}[/red]")


def create_pyproject_toml(directory: str, toolkit_name: str, author: str, description: str) -> None:
    """
    Create a pyproject.toml file for the new toolkit.
    """

    content = f"""
[tool.poetry]
name = "{toolkit_name}"
version = "0.1.0"
description = "{description}"
authors = ["{author}"]

[tool.poetry.dependencies]
python = "{DEFAULT_VERSIONS["python"]}"
arcade-ai = "{DEFAULT_VERSIONS["arcade-ai"]}"

[tool.poetry.dev-dependencies]
pytest = "{DEFAULT_VERSIONS["pytest"]}"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    create_file(os.path.join(directory, "pyproject.toml"), content.strip())


def create_new_toolkit(directory: str) -> None:
    """Generate a new Toolkit package based on user input."""
    name = ask_question("Name of the new toolkit?")
    toolkit_name = f"arcade_{name}"

    # Check for illegal characters in the toolkit name
    if not re.match(r"^[\w_]+$", toolkit_name):
        console.print(
            dedent(
                "[red]Toolkit name contains illegal characters. \
            Only alphanumeric characters and underscores are allowed.[/red]"
            )
        )
        return

    description = ask_question("Description of the toolkit?")
    author_name = ask_question("Author's name?")
    author_email = ask_question("Author's email?")
    author = f"{author_name} <{author_email}>"

    generate_test_dir = ask_question("Generate test directory? (yes/no)", "yes") == "yes"
    generate_eval_dir = ask_question("Generate eval directory? (yes/no)", "yes") == "yes"

    top_level_dir = os.path.join(directory, name)
    toolkit_dir = os.path.join(directory, name, toolkit_name)

    # Create the top level toolkit directory
    create_directory(top_level_dir)
    # Create the toolkit directory
    create_directory(toolkit_dir)

    # Create the tools directory
    create_directory(os.path.join(toolkit_dir, "tools"))

    # Create the __init__.py file in the tools directory
    create_file(os.path.join(toolkit_dir, "tools", "__init__.py"), "")

    # Create the hello.py file in the tools directory
    docstring = '"""Say a greeting!"""'
    create_file(
        os.path.join(toolkit_dir, "tools", "hello.py"),
        dedent(
            f"""
        from arcade.sdk import tool

        @tool
        def hello() -> str:
            {docstring}

            return "Hello, World!"
        """
        ).strip(),
    )

    # Create the pyproject.toml file
    create_pyproject_toml(top_level_dir, toolkit_name, author, description)

    # If the user wants to generate a test directory
    if generate_test_dir:
        create_directory(os.path.join(top_level_dir, "tests"))

    # If the user wants to generate an eval directory
    if generate_eval_dir:
        create_directory(os.path.join(top_level_dir, "evals"))

    console.print(f"[green]Toolkit {toolkit_name} has been created.[/green]")
