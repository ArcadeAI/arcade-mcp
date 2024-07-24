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
    toolkit: str = typer.Argument(..., help="The toolkit to show the tools of"),
    actor: Optional[str] = typer.Option(None, help="A running actor address to list tools from"),
) -> None:
    """
    Show the available tools in an actor or toolkit
    """
    from arcade.core.catalog import ToolCatalog
    from arcade.core.toolkit import Toolkit

    try:
        # load the toolkit from python package
        loaded_toolkit = Toolkit.from_package(toolkit)

        # create a tool catalog and add the toolkit
        catalog = ToolCatalog()
        catalog.add_toolkit(loaded_toolkit)

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
def run(  # noqa: C901
    toolkit: str = typer.Argument(..., help="The toolkit to add to model calls"),
    prompt: str = typer.Argument(..., help="The prompt to use for context"),
    model: str = typer.Option("gpt-3.5-turbo", "-m", help="The model to use for prediction."),
    tool: str = typer.Option(None, "-t", "--tool", help="The name of the tool to run."),
    choice: str = typer.Option(
        "prompt", "-c", "--choice", help="The value of the tool choice argument"
    ),
    stream: bool = typer.Option(True, "-s", "--stream", help="Stream the tool output."),
    actor: Optional[str] = typer.Option(
        None, "-a", "--actor", help="The actor to use for prediction."
    ),
) -> None:
    """
    Run a tool using an LLM to predict the arguments.
    """
    from arcade.core.catalog import ToolCatalog
    from arcade.core.client import EngineClient
    from arcade.core.executor import ToolExecutor
    from arcade.core.toolkit import Toolkit

    try:
        # load the toolkit from python package
        loaded_toolkit = Toolkit.from_package(toolkit)

        # create a tool catalog and add the toolkit
        catalog = ToolCatalog()
        catalog.add_toolkit(loaded_toolkit)

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

        if catalog.is_empty():
            console.print(f"❌ No tools found in toolkit: {toolkit}", style="bold red")
            raise typer.Exit(code=1)

        # TODO put in the engine url from config
        client = EngineClient()
        # TODO better way of doing this
        tool_choice = "required" if choice in ["prompt", "execute"] else choice
        calls = client.call_tool(tools, tool_choice=tool_choice, prompt=prompt, model=model)

        messages = [
            {"role": "user", "content": prompt},
        ]

        for tool_name, parameters in calls.items():
            called_tool = catalog[tool_name]
            console.print(f"Running tool: {tool_name} with params: {parameters}", style="bold blue")

            # TODO async.gather instead of loop.
            output = asyncio.run(
                ToolExecutor.run(
                    called_tool.tool,
                    called_tool.input_model,
                    called_tool.output_model,
                    **parameters,
                )
            )
            if output.code != 200:
                console.print(output.msg, style="bold red")
                if output.data:
                    console.print(output.data.result, style="bold red")
            else:
                if choice == "prompt":
                    # TODO: Add the tool results to the response in a safer way
                    messages += [
                        {
                            "role": "assistant",
                            # TODO: escape the output and ensure serialization works
                            "content": f"Results of Tool {tool_name}: {output.data.result!s}",  # type: ignore[union-attr]
                        },
                    ]
                    if stream:
                        stream_response = client.stream_complete(model=model, messages=messages)
                        display_streamed_markdown(stream_response)
                    else:
                        response = client.complete(model=model, messages=messages)
                        console.print(response.choices[0].message.content, style="bold green")
                elif choice == "execute":
                    console.print(output.data.result, style="green")  # type: ignore[union-attr]

    except RuntimeError as e:
        error_message = f"❌ Failed to run tool{': '+ escape(str(e)) if str(e) else ''}"
        console.print(error_message, style="bold red")


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
    name: str = typer.Option(None, "--name", "-n", help="The name of the configuration to edit"),
    val: str = typer.Option(None, "--val", "-v", help="The value of the configuration to edit"),
) -> None:
    """
    Show/edit configuration details of the Arcade Engine
    """
    pass


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
