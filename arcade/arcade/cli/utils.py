from typing import TYPE_CHECKING, Any

import typer
from openai.resources.chat.completions import ChatCompletionChunk, Stream
from rich.console import Console
from rich.markdown import Markdown
from typer.core import TyperGroup
from typer.models import Context

from arcade.core.catalog import ToolCatalog
from arcade.core.config_model import Config
from arcade.core.toolkit import Toolkit

if TYPE_CHECKING:
    from arcade.sdk.eval.eval import EvaluationResult

console = Console()


class OrderCommands(TyperGroup):
    def list_commands(self, ctx: Context) -> list[str]:  # type: ignore[override]
        """Return list of commands in the order appear."""
        return list(self.commands)  # get commands using self.commands


def create_cli_catalog(
    toolkit: str | None = None,
    show_toolkits: bool = False,
) -> ToolCatalog:
    """
    Load toolkits from the python environment.
    """
    if toolkit:
        try:
            prefixed_toolkit = "arcade_" + toolkit
            toolkits = [Toolkit.from_package(prefixed_toolkit)]
        except ValueError:
            try:  # try without prefix
                toolkits = [Toolkit.from_package(toolkit)]
            except ValueError as e:
                console.print(f"❌ {e}", style="bold red")
                typer.Exit(code=1)
    else:
        toolkits = Toolkit.find_all_arcade_toolkits()

    if not toolkits:
        console.print("❌ No toolkits found or specified", style="bold red")
        typer.Exit(code=1)

    catalog = ToolCatalog()
    for loaded_toolkit in toolkits:
        if show_toolkits:
            console.print(f"Loading toolkit: {loaded_toolkit.name}", style="bold blue")
        catalog.add_toolkit(loaded_toolkit)
    return catalog


def display_streamed_markdown(stream: Stream[ChatCompletionChunk], model: str) -> tuple[str, str]:
    """
    Display the streamed markdown chunks as a single line.
    """
    from rich.live import Live

    full_message = ""
    role = ""
    with Live(console=console, refresh_per_second=10) as live:
        for chunk in stream:
            choice = chunk.choices[0]
            chunk_message = choice.delta.content
            if role == "":
                role = choice.delta.role or ""
                if role == "assistant":
                    console.print(f"\n[bold blue]Assistant ({model}):[/bold blue] ")
            if chunk_message:
                full_message += chunk_message
                markdown_chunk = Markdown(full_message)
                live.update(markdown_chunk)

        # Markdownify URLs in the final message if applicable
        if role == "assistant":
            full_message = markdownify_urls(full_message)
            live.update(Markdown(full_message))

    return role, full_message


def markdownify_urls(message: str) -> str:
    """
    Convert URLs in the message to markdown links.
    """
    import re

    # This regex will match URLs that are not already formatted as markdown links:
    # [Link text](https://example.com)
    url_pattern = r"(?<!\]\()https?://\S+"

    # Wrap all URLs in the message with markdown links
    return re.sub(url_pattern, r"[Link](\g<0>)", message)


def validate_and_get_config(
    validate_engine: bool = True,
    validate_api: bool = True,
    validate_user: bool = True,
) -> Config:
    """
    Validates the configuration, user, and returns the Config object
    """
    from arcade.core.config import config

    if validate_engine and (not config.engine or not config.engine_url):
        console.print("❌ Engine configuration not found or URL is missing.", style="bold red")
        raise typer.Exit(code=1)

    if validate_api and (not config.api or not config.api.key):
        console.print(
            "❌ API configuration not found or key is missing. Please run `arcade login`.",
            style="bold red",
        )
        raise typer.Exit(code=1)

    if validate_user and (not config.user or not config.user.email):
        console.print(
            "❌ User email not found in configuration. Please run `arcade login`.", style="bold red"
        )
        raise typer.Exit(code=1)

    return config


def apply_config_overrides(
    config: Config, host_input: str | None, port_input: int | None, tls_input: bool | None
) -> None:
    """
    Apply optional config overrides (passed by the user) to the config object.
    """

    if not config.engine:
        # Should not happen, validate_and_get_config ensures that `engine` is set
        raise ValueError("Engine configuration not found in config.")

    # Special case for "localhost" and nothing else specified:
    # default to dev port and no TLS for convenience
    if host_input == "localhost":
        if port_input is None:
            port_input = 9099
        if tls_input is None:
            tls_input = False

    if host_input:
        config.engine.host = host_input

    if port_input is not None:
        config.engine.port = port_input

    if tls_input is not None:
        config.engine.tls = tls_input


def display_eval_results(results: list[dict[str, Any]], show_details: bool = False) -> None:
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

    for model_results in results:
        model = model_results.get("model", "Unknown Model")
        rubric = model_results.get("rubric", "Unknown Rubric")
        cases = model_results.get("cases", [])
        total_cases += len(cases)

        console.print(f"\n[bold magenta]Model: {model}[/bold magenta]\n")
        console.print(f"[bold magenta]{rubric}[/bold magenta]\n")

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

            # Display one-line summary for each case
            console.print(f"{status} {case['name']} -- Score: {evaluation.score:.2f}")

            if show_details:
                # Show detailed information for each case
                console.print(f"[bold]User Input:[/bold] {case['input']}\n")
                console.print("[bold]Details:[/bold]")
                console.print(_format_evaluation(evaluation))
                console.print("-" * 80)

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    console.print(f"Total Cases: {total_cases}")
    console.print(f"[green]Passed: {total_passed}[/green]")
    console.print(f"[yellow]Warnings: {total_warned}[/yellow]")
    console.print(f"[red]Failed: {total_failed}[/red]\n")


def _format_evaluation(evaluation: "EvaluationResult") -> str:
    """
    Format evaluation results with color-coded matches and scores.

    Args:
        evaluation: An EvaluationResult object containing the evaluation results.

    Returns:
        A formatted string representation of the evaluation details.
    """
    result_lines = []
    for critic_result in evaluation.results:
        match_color = "green" if critic_result["match"] else "red"
        field = critic_result["field"]
        score = critic_result["score"]
        weight = critic_result["weight"]
        expected = critic_result["expected"]
        actual = critic_result["actual"]
        result_lines.append(
            f"[bold]{field}:[/bold] "
            f"[{match_color}]Match: {critic_result['match']}, "
            f"Score: {score:.2f}/{weight:.2f}[/{match_color}]"
            f"\n    Expected: {expected}"
            f"\n    Actual: {actual}"
        )
    return "\n".join(result_lines)
