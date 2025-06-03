import typer
from rich.console import Console
from rich.markup import escape

from arcade_cli.display import display_tool_details, display_tools_table
from arcade_cli.utils import create_cli_catalog, get_tools_from_engine


def show_logic(
    toolkit: str | None,
    tool: str | None,
    host: str,
    local: bool,
    port: int | None,
    force_tls: bool,
    force_no_tls: bool,
    debug: bool,
) -> None:
    """Wrapper function for the `arcade show` CLI command
    Handles the logic for showing tools/toolkits.
    """
    console = Console()
    try:
        if local:
            catalog = create_cli_catalog(toolkit=toolkit)
            tools = [t.definition for t in list(catalog)]
        else:
            tools = get_tools_from_engine(host, port, force_tls, force_no_tls, toolkit)

        if tool:
            # Display detailed information for the specified tool
            tool_def = next(
                (
                    t
                    for t in tools
                    if t.get_fully_qualified_name().name.lower() == tool.lower()
                    or str(t.get_fully_qualified_name()).lower() == tool.lower()
                ),
                None,
            )
            if not tool_def:
                console.print(f"❌ Tool '{tool}' not found.", style="bold red")
                typer.Exit(code=1)
            else:
                display_tool_details(tool_def)
        else:
            # Display the list of tools as a table
            display_tools_table(tools)

    except Exception as e:
        if debug:
            raise
        error_message = f"❌ Failed to list tools: {escape(str(e))}"
        console.print(error_message, style="bold red")
