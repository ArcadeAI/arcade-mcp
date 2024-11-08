import os
import re
from importlib.metadata import version as get_version
from textwrap import dedent
from typing import Optional

import typer
from rich.console import Console

console = Console()

# Retrieve the installed version of arcade-ai
try:
    VERSION = get_version("arcade-ai")
except Exception as e:
    console.print(f"[red]Failed to get arcade-ai version: {e}[/red]")
    VERSION = "0.0.0"  # Default version if unable to fetch

DEFAULT_VERSIONS = {
    "python": "^3.10",
    "arcade-ai": f"~{VERSION}",  # allow patch version updates
    "pytest": "^8.3.0",
}


def ask_question(question: str, default: Optional[str] = None) -> str:
    """
    Ask a question via input() and return the answer.
    """
    answer = typer.prompt(question, default=default)
    if not answer and default:
        return default
    return str(answer)


def create_directory(path: str) -> bool:
    """
    Create a directory if it doesn't exist.
    Returns True if the directory was created, False if failed to create.
    """
    try:
        os.makedirs(path, exist_ok=False)
    except FileExistsError:
        console.print(f"[red]Directory '{path}' already exists.[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Failed to create directory {path}: {e}[/red]")
        return False
    return True


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
    while True:
        name = ask_question("Name of the new toolkit?")
        toolkit_name = name if name.startswith("arcade_") else f"arcade_{name}"

        # Check for illegal characters in the toolkit name
        if re.match(r"^[\w_]+$", toolkit_name):
            break
        else:
            console.print(
                "[red]Toolkit name contains illegal characters. "
                "Only alphanumeric characters and underscores are allowed. "
                "Please try again.[/red]"
            )

    description = ask_question("Description of the toolkit?")
    author_name = ask_question("Author's name?")
    author_email = ask_question("Author's email?")
    author = f"{author_name} <{author_email}>"

    yes_options = ["yes", "y", "ye", "yea", "yeah", "true"]
    generate_test_dir = (
        ask_question("Generate test directory? (yes/no)", "yes").lower() in yes_options
    )
    generate_eval_dir = (
        ask_question("Generate eval directory? (yes/no)", "yes").lower() in yes_options
    )

    top_level_dir = os.path.join(directory, name)
    toolkit_dir = os.path.join(directory, name, toolkit_name)

    # Create the top level toolkit directory
    if not create_directory(top_level_dir):
        return

    # Create the toolkit directory
    create_directory(toolkit_dir)

    # Create the __init__.py file in the toolkit directory
    create_file(os.path.join(toolkit_dir, "__init__.py"), "")

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
        from typing import Annotated
        from arcade.sdk import tool

        @tool
        def hello(name: Annotated[str, "The name of the person to greet"]) -> str:
            {docstring}

            return "Hello, " + name + "!"
        """
        ).strip(),
    )

    # Create the pyproject.toml file
    create_pyproject_toml(top_level_dir, toolkit_name, author, description)

    # If the user wants to generate a test directory
    if generate_test_dir:
        create_directory(os.path.join(top_level_dir, "tests"))

        # Create the __init__.py file in the tests directory
        create_file(os.path.join(top_level_dir, "tests", "__init__.py"), "")

        # Create the test_hello.py file in the tests directory
        stripped_toolkit_name = toolkit_name.replace("arcade_", "")
        create_file(
            os.path.join(top_level_dir, "tests", f"test_{stripped_toolkit_name}.py"),
            dedent(
                f"""
            import pytest
            from arcade.sdk.errors import ToolExecutionError
            from {toolkit_name}.tools.hello import hello

            def test_hello():
                assert hello("developer") == "Hello, developer!"

            def test_hello_raises_error():
                with pytest.raises(ToolExecutionError):
                    hello(1)
            """
            ).strip(),
        )

    # If the user wants to generate an eval directory
    if generate_eval_dir:
        create_directory(os.path.join(top_level_dir, "evals"))

        # Create the eval_hello.py file
        stripped_toolkit_name = toolkit_name.replace("arcade_", "")
        create_file(
            os.path.join(top_level_dir, "evals", "eval_hello.py"),
            dedent(
                f"""
                import {toolkit_name}
                from {toolkit_name}.tools.hello import hello

                from arcade.sdk import ToolCatalog
                from arcade.sdk.eval import (
                    EvalRubric,
                    EvalSuite,
                    SimilarityCritic,
                    tool_eval,
                )

                # Evaluation rubric
                rubric = EvalRubric(
                    fail_threshold=0.85,
                    warn_threshold=0.95,
                )


                catalog = ToolCatalog()
                catalog.add_module({toolkit_name})


                @tool_eval()
                def {stripped_toolkit_name}_eval_suite():
                    suite = EvalSuite(
                        name="{stripped_toolkit_name} Tools Evaluation",
                        system_message="You are an AI assistant with access to {stripped_toolkit_name} tools. Use them to help the user with their tasks.",
                        catalog=catalog,
                        rubric=rubric,
                    )

                    suite.add_case(
                        name="Saying hello",
                        user_message="Say hello to the developer!!!!",
                        expected_tool_calls=[
                            (
                                hello,
                                {{
                                    "name": "developer"
                                }}
                            )
                        ],
                        rubric=rubric,
                        critics=[
                            SimilarityCritic(critic_field="name", weight=0.5),
                        ],
                    )

                    return suite
                """
            ).strip(),
        )

    console.print(f"[green]Toolkit {toolkit_name} has been created in {top_level_dir} [/green]")
