from typing import Optional

from rich.markup import escape

from arcade_cli.display import display_tool_details, display_tools_table
from arcade_cli.utils import (
    CLIError,
    create_cli_catalog,
    create_cli_catalog_local,
    get_tools_from_engine,
    handle_cli_error,
)


def show_logic(
    toolkit: Optional[str],
    tool: Optional[str],
    host: str,
    local: bool,
    port: Optional[int],
    force_tls: bool,
    force_no_tls: bool,
    worker: bool,
    debug: bool,
) -> None:
    """Wrapper function for the `arcade show` CLI command
    Handles the logic for showing tools/toolkits.
    """
    try:
        if local:
            catalog = create_cli_catalog() if toolkit else create_cli_catalog_local()
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
                handle_cli_error(f"Tool '{tool}' not found.")
            else:
                display_tool_details(tool_def, worker=worker)
        else:
            # Display the list of tools as a table
            display_tools_table(tools)

    except CLIError:
        raise
    except Exception as e:
        handle_cli_error(f"Failed to list tools: {escape(str(e))}", debug=debug)
