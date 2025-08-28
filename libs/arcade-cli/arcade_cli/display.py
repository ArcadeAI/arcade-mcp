from typing import TYPE_CHECKING, Any

from arcade_core.schema import ToolDefinition
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from arcade_evals.eval import EvaluationResult
console = Console()


def display_tools_table(tools: list[ToolDefinition]) -> None:
    """
    Display a table of tools with their name, description, package, and version.
    """
    if not tools:
        console.print("No tools found.", style="bold")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name")
    table.add_column("Description")
    table.add_column("Package")
    table.add_column("Version")

    for tool in sorted(tools, key=lambda x: x.toolkit.name):
        table.add_row(
            str(tool.get_fully_qualified_name()),
            tool.description.split("\n")[0] if tool.description else "",
            tool.toolkit.name,
            tool.toolkit.version,
        )
    console.print(f"Found {len(tools)} tools.")
    console.print(table)


def display_tool_details(tool: ToolDefinition, worker: bool = False) -> None:  # noqa: C901
    """
    Display detailed information about a specific tool using multiple panels.

    Args:
        tool: The tool definition to display
        worker: If True, show full worker response structure. If False, show only value structure.
    """
    # Description Panel
    description_panel = Panel(
        tool.description or "No description available.",
        title=f"Tool: {tool.name}",
        border_style="cyan",
    )

    # Inputs Panel
    inputs = tool.input.parameters
    if inputs:
        inputs_table = Table(show_header=True, header_style="bold green")
        inputs_table.add_column("Name", style="cyan")
        inputs_table.add_column("Type", style="magenta")
        inputs_table.add_column("Required", style="yellow")
        inputs_table.add_column("Description", style="white")

        for param in inputs:
            # Format the type string properly
            type_str = _format_type_string(param.value_schema)

            # Add the main parameter row
            inputs_table.add_row(
                param.name,
                type_str,
                str(param.required),
                param.description or "",
            )

            # If this is a json type with properties, show them
            if (
                param.value_schema.val_type == "json"
                and hasattr(param.value_schema, "properties")
                and param.value_schema.properties
            ):
                _add_nested_properties(inputs_table, param.value_schema.properties, indent=1)
            # Handle arrays with inner properties
            elif (
                param.value_schema.val_type == "array"
                and hasattr(param.value_schema, "inner_properties")
                and param.value_schema.inner_properties
            ):
                _add_nested_properties(
                    inputs_table, param.value_schema.inner_properties, indent=1, is_array_item=True
                )

        inputs_panel = Panel(
            inputs_table,
            title="Input Parameters",
            border_style="green",
        )
    else:
        inputs_panel = Panel(
            "No input parameters.",
            title="Input Parameters",
            border_style="green",
        )

    # Output Panel - Show different levels based on worker flag
    output = tool.output
    if output and output.value_schema:
        output_table = Table(show_header=True, header_style="bold blue")
        output_table.add_column("Field", style="cyan")
        output_table.add_column("Type", style="magenta")
        output_table.add_column("Description", style="white")

        if worker:
            # Show full worker response structure
            output_table.add_row(
                "[bold]Response Structure[/bold]",
                "",
                "[dim]The tool response follows this structure:[/dim]",
            )

            # Available modes determine which fields can be present
            modes = output.available_modes

            if "value" in modes:
                # Show the value field with its schema
                value_type: str = output.value_schema.val_type
                display_type: str = value_type  # Separate variable for display string
                if value_type == "array" and output.value_schema.inner_val_type:
                    display_type = rf"array\[{output.value_schema.inner_val_type}]"
                elif output.value_schema.enum:
                    display_type = f"{value_type} (enum: {', '.join(output.value_schema.enum)})"

                output_table.add_row(
                    "  value",
                    display_type,
                    output.description or "The successful result from the tool",
                )

                # If the value is a json type with properties, show them
                if (
                    output.value_schema.val_type == "json"
                    and hasattr(output.value_schema, "properties")
                    and output.value_schema.properties
                ):
                    _add_nested_properties(output_table, output.value_schema.properties, indent=2)

            if "error" in modes:
                output_table.add_row(
                    "  error", "object", "[dim]Error details if the tool fails[/dim]"
                )
                output_table.add_row(
                    "    message", "string", "[dim]User-facing error message[/dim]"
                )
                output_table.add_row(
                    "    developer_message",
                    "string?",
                    "[dim]Technical error details (optional)[/dim]",
                )

            if "null" in modes:
                output_table.add_row("  value", "null", "[dim]Tool can return null/None[/dim]")

            # Additional fields that may be present
            output_table.add_row("", "", "")
            output_table.add_row(
                "[bold]Additional Fields[/bold]",
                "",
                "[dim]May be present in any response:[/dim]",
            )
            output_table.add_row(
                "  logs", "array?", "[dim]Optional warnings or info messages[/dim]"
            )
            output_table.add_row(
                "  requires_authorization",
                "object?",
                "[dim]OAuth flow details if auth needed[/dim]",
            )
        else:
            # Show only the value structure (simplified view)
            # Show the value type and description
            display_type = _format_type_string(output.value_schema)
            if output.value_schema.enum:
                display_type = (
                    f"{output.value_schema.val_type} (enum: {', '.join(output.value_schema.enum)})"
                )

            output_table.add_row(
                "[bold]Value[/bold]",
                display_type,
                output.description or "The return value from the tool",
            )

            # If the value is a json type with properties, show them
            if (
                output.value_schema.val_type == "json"
                and hasattr(output.value_schema, "properties")
                and output.value_schema.properties
            ):
                _add_nested_properties(output_table, output.value_schema.properties, indent=1)

        # Create subtitle with modes info
        modes_text = Text()
        modes_text.append("Response Modes: ", style="bold")
        modes_text.append("One of { ", style="dim")
        for i, mode in enumerate(output.available_modes):
            if i > 0:
                modes_text.append(", ", style="dim")
            if mode == "value":
                modes_text.append(mode, style="green")
            elif mode == "error":
                modes_text.append(mode, style="red")
            elif mode == "null":
                modes_text.append(mode, style="yellow")
            else:
                modes_text.append(mode, style="magenta")
        modes_text.append(" }", style="dim")

        output_panel = Panel(
            output_table,
            title="Output Schema",
            border_style="blue",
            subtitle=modes_text,
        )
    else:
        # No schema defined
        no_schema_table = Table(show_header=False)
        no_schema_table.add_column()

        if worker:
            no_schema_table.add_row(
                "[dim]No output schema defined. The tool response will follow this structure:[/dim]"
            )
            no_schema_table.add_row("")
            no_schema_table.add_row("[cyan]Response Structure:[/cyan]")
            no_schema_table.add_row("  • [bold]value[/bold]: null (when successful)")
            no_schema_table.add_row("  • [bold]error[/bold]: object (when failed)")
            no_schema_table.add_row("  • [bold]logs[/bold]: array? (optional warnings/info)")
        else:
            no_schema_table.add_row("[dim]No output schema defined.[/dim]")
            no_schema_table.add_row("")
            no_schema_table.add_row("The tool returns: [bold]null[/bold]")

        output_panel = Panel(
            no_schema_table,
            title="Output Schema",
            border_style="blue",
        )

    # Combine all panels vertically
    console.print(description_panel)
    console.print(inputs_panel)
    console.print(output_panel)


def _add_nested_properties(
    table: Table,
    properties: dict[str, Any],
    indent: int = 0,
    is_array_item: bool = False,
) -> None:
    """
    Recursively add nested properties to the table.

    Args:
        table: The Rich table to add rows to
        properties: Dictionary of property names to ValueSchema objects
        indent: Current indentation level
        is_array_item: Whether these properties are for array items
    """
    indent_prefix = "  " * indent

    # Show array item indicator if needed
    if is_array_item and indent > 0:
        # Get column count from the table
        num_columns = len(table.columns)

        # Create a row with the array indicator in the first column and empty strings for the rest
        row_data = [f"{indent_prefix[:-2]}[item]"] + [""] * (num_columns - 1)
        if num_columns >= 3:
            row_data[2] = "[dim]Each item in array:[/dim]"
        table.add_row(*row_data)

    for prop_name, prop_schema in properties.items():
        # Format the type string
        type_str = _format_type_string(prop_schema)

        # Add the property row with better descriptions
        description = ""
        # For nested properties, we don't have descriptions yet, but we could add them
        if hasattr(prop_schema, "description") and prop_schema.description:
            description = prop_schema.description

        # Create row data based on number of columns
        num_columns = len(table.columns)
        row_data = [f"{indent_prefix}{prop_name}", type_str]

        # For input parameter tables (4 columns), add empty required column
        if num_columns == 4:
            row_data.append("")  # Empty "Required" column for nested properties
            row_data.append(f"[dim]{description}[/dim]" if description else "")
        # For output tables (3 columns), just add description
        elif num_columns == 3:
            row_data.append(f"[dim]{description}[/dim]" if description else "")

        table.add_row(*row_data)

        # Recursively add nested properties if this is a json type with properties
        if (
            prop_schema.val_type == "json"
            and hasattr(prop_schema, "properties")
            and prop_schema.properties
        ):
            _add_nested_properties(table, prop_schema.properties, indent + 1)
        # Handle arrays with inner properties
        elif (
            prop_schema.val_type == "array"
            and hasattr(prop_schema, "inner_properties")
            and prop_schema.inner_properties
        ):
            _add_nested_properties(
                table, prop_schema.inner_properties, indent + 1, is_array_item=True
            )


def _format_type_string(schema: Any) -> str:
    """Format type string for display."""
    type_str: str = schema.val_type

    if schema.val_type == "array":
        if hasattr(schema, "inner_properties") and schema.inner_properties:
            type_str = r"array\[object]"
        elif schema.inner_val_type:
            type_str = rf"array\[{schema.inner_val_type}]"
    elif schema.enum:
        type_str = f"{type_str} (enum)"

    return type_str


def display_tool_messages(tool_messages: list[dict]) -> None:
    for message in tool_messages:
        if message["role"] == "assistant":
            for tool_call in message.get("tool_calls", []):
                console.print(
                    f"[bold]Called tool '{tool_call['function']['name']}' with parameters:[/bold] {tool_call['function']['arguments']}",
                    style="dim",
                )
        elif message["role"] == "tool":
            console.print(
                f"[bold]'{message['name']}' tool returned:[/bold] {message['content']}",
                style="dim",
            )


def display_eval_results(results: list[list[dict[str, Any]]], show_details: bool = False) -> None:
    """
    Display evaluation results in a format inspired by pytest's output.

    Args:
        results: List of dictionaries containing evaluation results for each model.
        show_details: Whether to show detailed results for each case.
    """
    total_passed = 0
    total_failed = 0
    total_warned = 0
    total_cases = 0

    for eval_suite in results:
        for model_results in eval_suite:
            model = model_results.get("model", "Unknown Model")
            rubric = model_results.get("rubric", "Unknown Rubric")
            cases = model_results.get("cases", [])
            total_cases += len(cases)

            console.print(f"[bold]Model:[/bold] [bold magenta]{model}[/bold magenta]")
            if show_details:
                console.print(f"[bold magenta]{rubric}[/bold magenta]")

            for case in cases:
                evaluation = case["evaluation"]
                status = (
                    "[green]PASSED[/green]"
                    if evaluation.passed
                    else "[yellow]WARNED[/yellow]"
                    if evaluation.warning
                    else "[red]FAILED[/red]"
                )
                if evaluation.passed:
                    total_passed += 1
                elif evaluation.warning:
                    total_warned += 1
                else:
                    total_failed += 1

                # Display one-line summary for each case with score as a percentage
                score_percentage = evaluation.score * 100
                console.print(f"{status} {case['name']} -- Score: {score_percentage:.2f}%")

                if show_details:
                    # Show detailed information for each case
                    console.print(f"[bold]User Input:[/bold] {case['input']}\n")
                    console.print("[bold]Details:[/bold]")
                    console.print(_format_evaluation(evaluation))
                    console.print("-" * 80)

    # Summary
    summary = (
        f"[bold]Summary -- [/bold]Total: {total_cases} -- [green]Passed: {total_passed}[/green]"
    )
    if total_warned > 0:
        summary += f" -- [yellow]Warnings: {total_warned}[/yellow]"
    if total_failed > 0:
        summary += f" -- [red]Failed: {total_failed}[/red]"
    console.print(summary + "\n")


def _format_evaluation(evaluation: "EvaluationResult") -> str:
    """
    Format evaluation results with color-coded matches and scores.

    Args:
        evaluation: An EvaluationResult object containing the evaluation results.

    Returns:
        A formatted string representation of the evaluation details.
    """
    result_lines = []
    if evaluation.failure_reason:
        result_lines.append(f"[bold red]Failure Reason:[/bold red] {evaluation.failure_reason}")
    else:
        for critic_result in evaluation.results:
            is_criticized = critic_result.get("is_criticized", True)
            match_color = (
                "yellow" if not is_criticized else "green" if critic_result["match"] else "red"
            )
            field = critic_result["field"]
            score = critic_result["score"]
            weight = critic_result["weight"]
            expected = critic_result["expected"]
            actual = critic_result["actual"]

            if is_criticized:
                result_lines.append(
                    f"[bold]{field}:[/bold] "
                    f"[{match_color}]Match: {critic_result['match']}"
                    f"\n     Score: {score:.2f}/{weight:.2f}[/{match_color}]"
                    f"\n     Expected: {expected}"
                    f"\n     Actual: {actual}"
                )
            else:
                result_lines.append(
                    f"[bold]{field}:[/bold] "
                    f"[{match_color}]Un-criticized[/{match_color}]"
                    f"\n     Expected: {expected}"
                    f"\n     Actual: {actual}"
                )
    return "\n".join(result_lines)


def display_arcade_chat_header(base_url: str, stream: bool) -> None:
    chat_header = Text.assemble(
        "\n",
        (
            "=== Arcade Chat ===",
            "bold magenta underline",
        ),
        "\n",
        "\n",
        "Chatting with Arcade Engine at ",
        (
            base_url,
            "bold blue",
        ),
    )
    if stream:
        chat_header.append(" (streaming)")
    console.print(chat_header)
