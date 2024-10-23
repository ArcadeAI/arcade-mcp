import importlib.util
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Union, cast

import typer
from arcadepy import NOT_GIVEN, APIConnectionError, APIStatusError, APITimeoutError, Arcade
from arcadepy.types import AuthorizationResponse
from openai import OpenAI
from openai.resources.chat.completions import ChatCompletionChunk, Stream
from openai.types.chat.chat_completion import Choice as ChatCompletionChoice
from openai.types.chat.chat_completion_chunk import Choice as ChatCompletionChunkChoice
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from typer.core import TyperGroup
from typer.models import Context

from arcade.core.catalog import ToolCatalog
from arcade.core.config_model import Config
from arcade.core.errors import ToolkitLoadError
from arcade.core.schema import ToolDefinition
from arcade.core.toolkit import Toolkit

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


def get_config_with_overrides(
    force_tls: bool,
    force_no_tls: bool,
    host_input: str | None = None,
    port_input: int | None = None,
) -> Config:
    """
    Get the config with CLI-specific optional overrides applied.
    """
    config = validate_and_get_config()

    if not force_tls and not force_no_tls:
        tls_input = None
    elif force_no_tls:
        tls_input = False
    else:
        tls_input = True
    apply_config_overrides(config, host_input, port_input, tls_input)
    return config


def get_tools_from_engine(
    host: str,
    port: int | None = None,
    force_tls: bool = False,
    force_no_tls: bool = False,
    toolkit: str | None = None,
) -> list[ToolDefinition]:
    config = get_config_with_overrides(force_tls, force_no_tls, host, port)
    client = Arcade(api_key=config.api.key, base_url=config.engine_url)

    tools = []
    # TODO: This is a hack! limit=100 is a workaround for broken(?) pagination in Stainless
    for page in client.tools.list(limit=100, toolkit=toolkit or NOT_GIVEN).iter_pages():
        for item in page:
            tools.append(ToolDefinition.model_validate(item.model_dump()))

    return tools


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
    printed_role: bool = False

    with Live(console=console, refresh_per_second=10) as live:
        for chunk in stream:
            choice = chunk.choices[0]
            role = choice.delta.role or role

            # Display and get tool messages if they exist
            tool_messages += get_tool_messages(choice)  # type: ignore[arg-type]
            tool_authorization = get_tool_authorization(choice)

            chunk_message = choice.delta.content

            if role == "assistant" and tool_authorization:
                continue  # Skip the message if it's an auth request (handled later in handle_tool_authorization)

            if role == "assistant" and not printed_role:
                console.print(f"\n[blue][bold]Assistant[/bold] ({model}):[/blue] ")
                printed_role = True

            if chunk_message:
                full_message += chunk_message
                markdown_chunk = Markdown(full_message)
                live.update(markdown_chunk)

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


def log_engine_health(client: Arcade) -> None:
    try:
        result = client.health.check(timeout=2)
        if result.healthy:
            return

        console.print(
            "⚠️ Warning: Arcade Engine is unhealthy",
            style="bold yellow",
        )

    except APIConnectionError:
        console.print(
            "⚠️ Warning: Arcade Engine was unreachable. (Is it running?)",
            style="bold yellow",
        )

    except APIStatusError as e:
        console.print(
            "[bold][yellow]⚠️ Warning: "
            + str(e)
            + " ("
            + "[/yellow]"
            + "[red]"
            + str(e.status_code)
            + "[/red]"
            + "[yellow])[/yellow][/bold]"
        )


@dataclass
class ChatInteractionResult:
    history: list[dict]
    tool_messages: list[dict]
    tool_authorization: dict | None


def handle_chat_interaction(
    client: OpenAI, model: str, history: list[dict], user_email: str | None, stream: bool = False
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

        if role == "assistant" and tool_authorization:
            pass  # Skip the message if it's an auth request (handled later in handle_tool_authorization)
        elif role == "assistant":
            message_content = markdownify_urls(message_content)
            console.print(
                f"\n[blue][bold]Assistant[/bold] ({model}):[/blue] ", Markdown(message_content)
            )
        else:
            console.print(f"\n[bold]{role}:[/bold] {message_content}")

    history += tool_messages
    history.append({"role": role, "content": message_content})

    return ChatInteractionResult(history, tool_messages, tool_authorization)


def handle_tool_authorization(
    arcade_client: Arcade,
    tool_authorization: AuthorizationResponse,
    history: list[dict[str, Any]],
    openai_client: OpenAI,
    model: str,
    user_email: str | None,
    stream: bool,
) -> ChatInteractionResult:
    with Live(console=console, refresh_per_second=4) as live:
        if tool_authorization.authorization_url:
            authorization_url = str(tool_authorization.authorization_url)
            webbrowser.open(authorization_url)
            message = (
                "You'll need to authorize this action in your browser.\n\n"
                f"If a browser doesn't open automatically, click [this link]({authorization_url}) "
                f"or copy this URL and paste it into your browser:\n\n{authorization_url}"
            )
            live.update(Markdown(message, style="dim"))

        wait_for_authorization_completion(arcade_client, tool_authorization)

        message = "Thanks for authorizing the action! Sending your request..."
        live.update(Text(message, style="dim"))

    history.pop()
    return handle_chat_interaction(openai_client, model, history, user_email, stream)


def wait_for_authorization_completion(
    client: Arcade, tool_authorization: AuthorizationResponse | None
) -> None:
    """
    Wait for the authorization for a tool call to complete i.e., wait for the user to click on
    the approval link and authorize Arcade.
    """
    if tool_authorization is None:
        return

    auth_response = AuthorizationResponse.model_validate(tool_authorization)

    while auth_response.status != "completed":
        try:
            auth_response = client.auth.status(
                authorization_id=cast(str, auth_response.authorization_id),
                scopes=" ".join(auth_response.scopes) if auth_response.scopes else NOT_GIVEN,
                wait=59,
            )
        except APITimeoutError:
            continue


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


def get_eval_files(directory: str) -> list[Path]:
    """
    Get a list of evaluation files starting with 'eval_' and ending with '.py' in the given directory.

    Args:
        directory: The directory to search for evaluation files.

    Returns:
        A list of Paths to the evaluation files. Returns an empty list if no files are found.
    """
    directory_path = Path(directory).resolve()

    if directory_path.is_dir():
        eval_files = [
            f
            for f in directory_path.iterdir()
            if f.is_file() and f.name.startswith("eval_") and f.name.endswith(".py")
        ]
    elif directory_path.is_file():
        eval_files = (
            [directory_path]
            if directory_path.name.startswith("eval_") and directory_path.name.endswith(".py")
            else []
        )
    else:
        console.print(f"Path not found: {directory_path}", style="bold red")
        return []

    if not eval_files:
        console.print(
            "No evaluation files found. Filenames must start with 'eval_' and end with '.py'.",
            style="bold yellow",
        )
        return []

    return eval_files


def load_eval_suites(eval_files: list[Path]) -> list[Callable]:
    """
    Load evaluation suites from the given eval_files by importing the modules
    and extracting functions decorated with `@tool_eval`.

    Args:
        eval_files: A list of Paths to evaluation files.

    Returns:
        A list of callable evaluation suite functions.
    """
    eval_suites = []
    for eval_file_path in eval_files:
        module_name = eval_file_path.stem  # filename without extension

        # Now we need to load the module from eval_file_path
        file_path_str = str(eval_file_path)
        module_name_str = module_name

        # Load using importlib
        spec = importlib.util.spec_from_file_location(module_name_str, file_path_str)
        if spec is None:
            console.print(f"Failed to load {eval_file_path}", style="bold red")
            continue

        module = importlib.util.module_from_spec(spec)
        if spec.loader is not None:
            spec.loader.exec_module(module)
        else:
            console.print(f"Failed to load module: {module_name}", style="bold red")
            continue

        eval_suite_funcs = [
            obj
            for name, obj in module.__dict__.items()
            if callable(obj) and hasattr(obj, "__tool_eval__")
        ]

        if not eval_suite_funcs:
            console.print(f"No @tool_eval functions found in {eval_file_path}", style="bold yellow")
            continue

        eval_suites.extend(eval_suite_funcs)

    return eval_suites
