import asyncio
import os
from typing import Optional

import typer
from openai.resources.chat.completions import ChatCompletionChunk, Stream
from rich.console import Console
from rich.markdown import Markdown
from rich.markup import escape
from rich.table import Table
from typer.core import TyperGroup
from typer.models import Context

from arcade.core.catalog import ToolCatalog
from arcade.core.config import Config
from arcade.core.schema import ToolContext
from arcade.core.toolkit import Toolkit


class OrderCommands(TyperGroup):
    def list_commands(self, ctx: Context) -> list[str]:  # type: ignore[override]
        """Return list of commands in the order appear."""
        return list(self.commands)  # get commands using self.commands


console = Console()
cli = typer.Typer(
    cls=OrderCommands,
)


@cli.command(help="Log in to Arcade Cloud")
def login(
    username: str = typer.Option(..., prompt="Username", help="Your Arcade Cloud username"),
    api_key: str = typer.Option(None, prompt="API Key", help="Your Arcade Cloud API Key"),
) -> None:
    """
    Logs the user into Arcade Cloud.
    """
    # Here you would add the logic to authenticate the user with Arcade Cloud
    pass


@cli.command(help="Log out of Arcade Cloud")
def logout() -> None:
    """
    Logs the user out of Arcade Cloud.
    """
    # Here you would add the logic to log the user out of Arcade Cloud
    pass


@cli.command(help="Create a new toolkit package directory")
def new(
    directory: str = typer.Option(os.getcwd(), "--dir", help="tools directory path"),
) -> None:
    """
    Creates a new toolkit with the given name, description, and result type.
    """
    from arcade.cli.new import create_new_toolkit

    try:
        create_new_toolkit(directory)
    except Exception as e:
        error_message = f"❌ Failed to create new Toolkit: {escape(str(e))}"
        console.print(error_message, style="bold red")


@cli.command(help="Show the available tools in an actor or toolkit directory")
def show(
    toolkit: Optional[str] = typer.Option(
        None, "-t", "--toolkit", help="The toolkit to show the tools of"
    ),
    all_toolkits: bool = typer.Option(False, "-a", "--all", help="Show all installed toolkits"),
    actor: Optional[str] = typer.Option(None, help="A running actor address to list tools from"),
) -> None:
    """
    Show the available tools in an actor or toolkit
    """

    try:
        catalog = create_cli_catalog(toolkit, all_toolkits)

        # Create a table with Rich library
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name")
        table.add_column("Description")
        table.add_column("Toolkit")
        table.add_column("Version")

        for tool in catalog:
            table.add_row(tool.name, tool.description, tool.meta.toolkit, tool.version)

        console.print(table)

    except Exception as e:
        # better error message here
        error_message = f"❌ Failed to List tools: {escape(str(e))}"
        console.print(error_message, style="bold red")


@cli.command(help="Run a tool using an LLM to predict the arguments")
def run(
    toolkit: Optional[str] = typer.Option(
        None, "-t", "--toolkit", help="The toolkit to include in the run"
    ),
    all_toolkits: bool = typer.Option(
        False, "-a", "--all", is_flag=True, help="Use all installed toolkits"
    ),
    model: str = typer.Option("gpt-4o", "-m", help="The model to use for prediction."),
    tool: str = typer.Option(None, "--tool", help="The name of the tool to run."),
    choice: str = typer.Option(
        "generate", "-c", "--choice", help="The value of the tool choice argument"
    ),
    stream: bool = typer.Option(
        False, "-s", "--stream", is_flag=True, help="Stream the tool output."
    ),
    actor: Optional[str] = typer.Option(None, "--actor", help="The actor to use for prediction."),
    prompt: str = typer.Argument(..., help="The prompt to use for context"),
) -> None:
    """
    Run a tool using an LLM to predict the arguments.
    """
    from arcade.core.client import EngineClient
    from arcade.core.executor import ToolExecutor

    try:
        catalog = create_cli_catalog(toolkit=toolkit, all_toolkits=all_toolkits)

        # if user specified a tool
        if tool:
            # check if the tool is in the catalog/toolkit
            if tool not in catalog:
                console.print(f"❌ Tool not found in toolkit: {toolkit}", style="bold red")
                raise typer.Exit(code=1)
            else:
                tools = [catalog[tool]]
        else:
            # use all the tools in the catalog
            tools = list(catalog)

        # TODO put in the engine url from config
        client = EngineClient()
        # TODO better way of doing this
        tool_choice = "required" if choice in ["generate", "execute"] else choice
        calls = client.call_tool(tools, tool_choice=tool_choice, prompt=prompt, model=model)

        messages = [
            {"role": "user", "content": prompt},
        ]
        for tool_name, parameters in calls.items():
            called_tool = catalog[tool_name]
            console.print(f"Calling tool: {tool_name} with params: {parameters}", style="bold blue")

            # TODO async.gather instead of loop.
            output = asyncio.run(
                ToolExecutor.run(
                    called_tool.tool,
                    called_tool.definition,
                    called_tool.input_model,
                    called_tool.output_model,
                    ToolContext(),
                    **parameters,
                )
            )
            if output.code != 200:
                console.print(output.msg, style="bold red")
                if output.data:
                    console.print(output.data.result, style="bold red")
                    typer.Exit(code=1)
            else:
                messages += [
                    {
                        "role": "assistant",
                        # TODO: escape the output and ensure serialization works
                        "content": f"Results of Tool {tool_name}: {output.data.result!s}",  # type: ignore[union-attr]
                    },
                ]

            if choice == "execute":
                console.print(output.data.result, style="green")  # type: ignore[union-attr]

        if stream:
            stream_response = client.stream_complete(model=model, messages=messages)
            display_streamed_markdown(stream_response)
        else:
            response = client.complete(model=model, messages=messages)
            console.print(response.choices[0].message.content, style="bold green")

    except RuntimeError as e:
        error_message = f"❌ Failed to run tool{': ' + escape(str(e)) if str(e) else ''}"
        console.print(error_message, style="bold red")


@cli.command(help="Chat with a language model")
def chat(
    model: str = typer.Option("gpt-4o-mini", "-m", help="The model to use for prediction."),
    choice: str = typer.Option(
        None, "-c", "--choice", help="The value of the tool choice argument"
    ),
    stream: bool = typer.Option(
        False, "-s", "--stream", is_flag=True, help="Stream the tool output."
    ),
    prompt: str = typer.Argument(..., help="The prompt to use for context"),
) -> None:
    """
    Run a tool using an LLM to predict the arguments.
    """
    from arcade.core.client import EngineClient

    client = EngineClient()
    try:
        messages = [
            {"role": "user", "content": prompt},
        ]

        if stream:
            stream_response = client.stream_complete(model=model, messages=messages)
            display_streamed_markdown(stream_response)
        else:
            response = client.complete(model=model, messages=messages)
            console.print(response.choices[0].message.content, style="bold green")

    except RuntimeError as e:
        error_message = f"❌ Failed to run tool{': ' + escape(str(e)) if str(e) else ''}"
        console.print(error_message, style="bold red")


@cli.command(help="Start an Actor server with specified configurations.")
def dev(
    host: str = typer.Option(
        "127.0.0.1", help="Host for the app, from settings by default.", show_default=True
    ),
    port: int = typer.Option("8000", help="Port for the app, defaults to ", show_default=True),
) -> None:
    """
    Starts the actor with host, port, and reload options. Uses
    Uvicorn as ASGI actor. Parameters allow runtime configuration.
    """
    from arcade.cli.serve import serve_default_actor

    try:
        serve_default_actor(host, port)
    except KeyboardInterrupt:
        console.print("actor stopped by user.", style="bold red")
        typer.Exit()
    except Exception as e:
        error_message = f"❌ Failed to start Arcade Actor: {escape(str(e))}"
        console.print(error_message, style="bold red")
        raise typer.Exit(code=1)


@cli.command(help="Manage the Arcade Engine (start/stop/restart)")
def engine(
    action: str = typer.Argument("start", help="The action to take (start/stop/restart)"),
    host: str = typer.Option("localhost", "--host", "-h", help="The host of the engine"),
    port: int = typer.Option(6901, "--port", "-p", help="The port of the engine"),
) -> None:
    """
    Manage the Arcade Engine (start/stop/restart)
    """
    pass


@cli.command(help="Manage credientials stored in the Arcade Engine")
def credentials(
    action: str = typer.Argument("show", help="The action to take (add/remove/show)"),
    name: str = typer.Option(None, "--name", "-n", help="The name of the credential to add/remove"),
    val: str = typer.Option(None, "--val", "-v", help="The value of the credential to add/remove"),
) -> None:
    """
    Manage credientials stored in the Arcade Engine
    """
    pass


@cli.command(help="Show/edit configuration details of the Arcade Engine")
def config(
    action: str = typer.Argument("show", help="The action to take (show/edit)"),
    key: str = typer.Option(
        None, "--key", "-k", help="The configuration key to edit (e.g., 'api.key')"
    ),
    val: str = typer.Option(None, "--val", "-v", help="The value of the configuration to edit"),
) -> None:
    """
    Show/edit configuration details of the Arcade Engine
    """

    config = Config.load_from_file()

    if action == "show":
        display_config_as_table(config)
    elif action == "edit":
        if not key or val is None:
            console.print("❌ Key and value must be provided for editing.", style="bold red")
            raise typer.Exit(code=1)

        keys = key.split(".")
        if len(keys) != 2:
            console.print("❌ Invalid key format. Use 'section.name' format.", style="bold red")
            raise typer.Exit(code=1)

        section, name = keys
        section_dict = getattr(config, section, None)
        if section_dict and hasattr(section_dict, name):
            setattr(section_dict, name, val)
            config.save_to_file()
            console.print("✅ Configuration updated successfully.", style="bold green")
        else:
            console.print(
                f"❌ Invalid configuration name: {name} in section: {section}", style="bold red"
            )
            raise typer.Exit(code=1)
    else:
        console.print(f"❌ Invalid action: {action}", style="bold red")
        raise typer.Exit(code=1)


def display_config_as_table(config: Config) -> None:
    """
    Display the configuration details as a table using Rich library.
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Section")
    table.add_column("Name")
    table.add_column("Value")

    for section_name in config.dict():
        section = getattr(config, section_name)
        if section:
            section = section.dict()
            first = True
            for name, value in section.items():
                if first:
                    table.add_row(section_name, name, str(value))
                    first = False
                else:
                    table.add_row("", name, str(value))
            table.add_row("", "", "")

    console.print(table)


def display_streamed_markdown(stream: Stream[ChatCompletionChunk]) -> None:
    """
    Display the streamed markdown chunks as a single line.
    """
    from rich.live import Live

    full_message = ""
    with Live(console=console, refresh_per_second=10) as live:
        for chunk in stream:
            choice = chunk.choices[0]
            chunk_message = choice.delta.content
            if chunk_message:
                full_message += chunk_message
                markdown_chunk = Markdown(full_message)
                live.update(markdown_chunk)


def create_cli_catalog(
    toolkit: str | None = None,
    all_toolkits: bool = False,
) -> ToolCatalog:
    """
    Load toolkits from the python environment.
    """

    if all_toolkits:
        toolkits = Toolkit.find_all_arcade_toolkits()
        if not toolkits:
            console.print("No toolkits found in Python environment.", style="bold red")
            raise typer.Exit(code=1)
    else:
        if not toolkit:
            console.print("No toolkit specified and '-a' not supplied.", style="bold red")
            raise typer.Exit(code=1)
        else:
            # load the toolkit from python package
            try:
                prefixed_toolkit = "arcade_" + toolkit
                toolkits = [Toolkit.from_package(prefixed_toolkit)]
            except ValueError:
                try:  # try without prefix
                    toolkits = [Toolkit.from_package(toolkit)]
                except ValueError as e:
                    console.print(f"❌ {e}", style="bold red")
                    raise typer.Exit(code=1)

    catalog = ToolCatalog()
    for loaded_toolkit in toolkits:
        console.print(f"Loading toolkit: {loaded_toolkit.name}", style="bold blue")
        catalog.add_toolkit(loaded_toolkit)
    return catalog
