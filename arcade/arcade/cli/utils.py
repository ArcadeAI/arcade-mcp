import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Union

import typer
from openai.resources.chat.completions import ChatCompletionChunk, Stream
from openai.types.chat.chat_completion import Choice as ChatCompletionChoice
from openai.types.chat.chat_completion_chunk import Choice as ChatCompletionChunkChoice
from rich.console import Console
from rich.markdown import Markdown
from typer.core import TyperGroup
from typer.models import Context

from arcade.client.client import Arcade
from arcade.client.schema import AuthResponse
from arcade.core.catalog import ToolCatalog
from arcade.core.config_model import Config
from arcade.core.errors import ToolkitLoadError
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
        except ToolkitLoadError:
            try:  # try without prefix
                toolkits = [Toolkit.from_package(toolkit)]
            except ToolkitLoadError as e:
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


def display_tool_messages(tool_messages: list[dict]) -> None:
    for message in tool_messages:
        if message["role"] == "assistant":
            for tool_call in message.get("tool_calls", []):
                console.print(
                    f"[bright_black][bold]Called tool '{tool_call['function']['name']}'[/bold]\n[bold]Parameters:[/bold]{tool_call['function']['arguments']}[/bright_black]"
                )
        elif message["role"] == "tool":
            console.print(
                f"[bright_black][bold]'{message['name']}' tool returned:[/bold]{message['content']}[/bright_black]"
            )


def get_tool_messages(choice: dict) -> list[dict]:
    if hasattr(choice, "tool_messages") and choice.tool_messages:
        return choice.tool_messages  # type: ignore[no-any-return]
    return []


@dataclass
class StreamingResult:
    role: str
    full_message: str
    tool_messages: list
    tool_authorization: dict | None


def handle_streaming_content(stream: Stream[ChatCompletionChunk], model: str) -> StreamingResult:
    """
    Display the streamed markdown chunks as a single line.
    """
    from rich.live import Live

    full_message = ""
    tool_messages = []
    tool_authorization = None
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

            # Display and get tool messages if they exist
            tool_messages += get_tool_messages(choice)  # type: ignore[arg-type]
            tool_authorization = get_tool_authorization(choice)

        # Markdownify URLs in the final message if applicable
        if role == "assistant":
            full_message = markdownify_urls(full_message)
            live.update(Markdown(full_message))

    return StreamingResult(role, full_message, tool_messages, tool_authorization)


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

                # Display one-line summary for each case
                console.print(f"{status} {case['name']} -- Score: {evaluation.score:.2f}")

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


@dataclass
class ChatInteractionResult:
    history: list[dict]
    tool_messages: list[dict]
    tool_authorization: dict | None


def handle_chat_interaction(
    client: Arcade, model: str, history: list[dict], user_email: str | None, stream: bool = False
) -> ChatInteractionResult:
    """
    Handle a single chat-request/chat-response interaction for both streamed and non-streamed responses.
    Handling the chat response includes:
    - Streaming the response if the stream flag is set
    - Displaying the response in the console
    - Getting the tool messages and tool authorization from the response
    - Updating the history with the response, tool calls, and tool responses
    """
    if stream:
        # TODO Fix this in the client so users don't deal with these
        # typing issues
        response = client.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=history,
            tool_choice="generate",
            user=user_email,
            stream=True,
        )
        streaming_result = handle_streaming_content(response, model)
        role, message_content = streaming_result.role, streaming_result.full_message
        tool_messages, tool_authorization = (
            streaming_result.tool_messages,
            streaming_result.tool_authorization,
        )
    else:
        response = client.chat.completions.create(  # type: ignore[call-overload]
            model=model,
            messages=history,
            tool_choice="generate",
            user=user_email,
            stream=False,
        )
        message_content = response.choices[0].message.content or ""

        # Get extra fields from the response
        tool_messages = get_tool_messages(response.choices[0])
        tool_authorization = get_tool_authorization(response.choices[0])

        role = response.choices[0].message.role
        if role == "assistant":
            message_content = markdownify_urls(message_content)
            console.print(
                f"\n[bold blue]Assistant ({model}):[/bold blue] ", Markdown(message_content)
            )
        else:
            console.print(f"\n[bold magenta]{role}:[/bold magenta] {message_content}")

    history += tool_messages
    history.append({"role": role, "content": message_content})

    return ChatInteractionResult(history, tool_messages, tool_authorization)


def wait_for_authorization_completion(client: Arcade, tool_authorization: dict | None) -> None:
    """
    Wait for the authorization for a tool call to complete i.e., wait for the user to click on
    the approval link and authorize Arcade.
    """
    if tool_authorization is None:
        return
    auth_response = AuthResponse.model_validate(tool_authorization)

    while auth_response.status != "completed":
        time.sleep(0.5)
        auth_response = client.auth.status(auth_response)


def get_tool_authorization(
    choice: Union[ChatCompletionChoice, ChatCompletionChunkChoice],
) -> dict | None:
    """
    Get the tool authorization from a chat response's choice.
    """
    if hasattr(choice, "tool_authorizations") and choice.tool_authorizations:
        return choice.tool_authorizations[0]  # type: ignore[no-any-return]
    return None


def is_authorization_pending(tool_authorization: dict | None) -> bool:
    """
    Check if the authorization for a tool call is pending.
    Expects a chat response's choice.tool_authorizations as input.
    """
    is_auth_pending = (
        tool_authorization is not None and tool_authorization.get("status", "") == "pending"
    )
    return is_auth_pending
