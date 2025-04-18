from typing import TYPE_CHECKING, Any

from rich.box import ROUNDED
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from arcade.cli.collect import (
    ProcessCollector,
    ProcessInfo,
    SystemCollector,
)
from arcade.core.schema import ToolDefinition

if TYPE_CHECKING:
    from arcade.sdk.eval.eval import EvaluationResult
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


def display_tool_details(tool: ToolDefinition) -> None:
    """
    Display detailed information about a specific tool using multiple panels.
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
        inputs_table.add_column("Default", style="blue")
        for param in inputs:
            # Since InputParameter does not have a default field, we use "N/A"
            default_value = "N/A"
            if param.value_schema.enum:
                default_value = f"One of {param.value_schema.enum}"
            inputs_table.add_row(
                param.name,
                param.value_schema.val_type,
                str(param.required),
                param.description or "",
                default_value,
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

    # Output Panel
    output = tool.output
    if output:
        output_description = output.description or "No description available."
        output_types = ", ".join(output.available_modes)
        output_val_type = output.value_schema.val_type if output.value_schema else "N/A"
        output_details = Text.assemble(
            ("Description: ", "bold"),
            (output_description, ""),
            "\n",
            ("Available Modes: ", "bold"),
            (output_types, ""),
            "\n",
            ("Value Type: ", "bold"),
            (output_val_type, ""),
        )
        output_panel = Panel(
            output_details,
            title="Expected Output",
            border_style="blue",
        )
    else:
        output_panel = Panel(
            "No output information available.",
            title="Expected Output",
            border_style="blue",
        )

    # Combine all panels vertically
    console.print(description_panel)
    console.print(inputs_panel)
    console.print(output_panel)


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
                f"[bold]'{message['name']}' tool returned:[/bold] {message['content']}", style="dim"
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


def display_all_info(system: SystemCollector, process: ProcessCollector):
    """
    Display system and process information in a compact layout
    """
    layout = Layout()

    # Create a very compact layout with minimal spacing
    layout.split_column(
        Layout(name="header", size=2),  # Header
        Layout(name="system_section", size=8, ratio=6),  # Combined system section
        Layout(name="process_section", size=10, ratio=6),  # Combined process section
        Layout(name="spacing1", size=1, ratio=1),
        Layout(name="process_connections"),  # Connections take remaining space
    )

    # Split system section into info and metrics
    layout["system_section"].split_row(
        Layout(name="system_info", ratio=1),
        Layout(name="system_metrics", ratio=1),
    )

    # Split process section into info and metrics
    layout["process_section"].split_row(
        Layout(name="process_info", ratio=1),
        Layout(name="process_metrics", ratio=1),
    )

    # Compact header with purple color
    header_text = Text(
        f"Arcade Stats: {process.process_info.name} (PID: {process.process_info.pid})",
        style="bold magenta",
    )
    layout["header"].update(header_text)

    # Add empty text for spacing
    layout["spacing1"].update(Text(""))

    # Update the initial system information
    layout["system_info"].update(system.system_info.as_rich_table())
    layout["system_metrics"].update(system.system_metrics.as_rich_table())
    layout["process_info"].update(proc_table(process.process_info))

    with Live(layout, refresh_per_second=2, screen=True) as live:
        while process.is_alive():
            try:
                system_stats = system.system_metrics
                process_stats = process.process_metrics

                # Get the process metrics tables
                proc_stat_table, connection_table = process_stats.as_rich_table()

                # Update the layout with the latest data
                layout["system_metrics"].update(system_stats.as_rich_table())
                layout["process_metrics"].update(proc_stat_table)
                layout["process_connections"].update(connection_table)
                live.refresh()
            except Exception as e:
                # Gracefully handle errors
                error_panel = Panel(
                    f"Error updating stats: {e!s}", title="Error", border_style="red"
                )
                layout["process_metrics"].update(error_panel)
                live.refresh()


def proc_table(proc_info: ProcessInfo):
    """Create a compact table for process information"""
    table = Table(
        title="Process Info",
        show_header=True,
        header_style="bold magenta",  # Changed to magenta/purple
        expand=True,
        box=ROUNDED,
        padding=(0, 0),  # Minimal padding
    )

    # Use one row to display all process info
    table.add_column("Property", style="bold dim", width=10)  # Grey
    table.add_column("Details", style="blue")  # Blue

    # Combine all info into a single row
    info = f"Name: {proc_info.name}, PID: {proc_info.pid}, User: {proc_info.username}"
    table.add_row("Process", info)

    return table
