import importlib.util
import ipaddress
import os
import shlex
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from importlib import metadata
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, Union, cast
from urllib.parse import urlencode, urlparse

import idna
import typer
from arcade_core import ToolCatalog, Toolkit
from arcade_core.config_model import Config
from arcade_core.errors import ToolkitLoadError
from arcade_core.schema import ToolDefinition
from arcadepy import NOT_GIVEN, APIConnectionError, APIStatusError, APITimeoutError, Arcade
from arcadepy.types import AuthorizationResponse
from openai import OpenAI, Stream
from openai.types.chat.chat_completion import Choice as ChatCompletionChoice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import Choice as ChatCompletionChunkChoice
from pydantic import ValidationError
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.text import Text
from typer.core import TyperGroup
from typer.models import Context

from arcade_cli.constants import LOCALHOST

console = Console()


# -----------------------------------------------------------------------------
# Shared helpers for the CLI
# -----------------------------------------------------------------------------


class OrderCommands(TyperGroup):
    def list_commands(self, ctx: Context) -> list[str]:  # type: ignore[override]
        """Return list of commands in the order appear."""
        return list(self.commands)  # get commands using self.commands


class ChatCommand(str, Enum):
    HELP = "/help"
    HELP_ALT = "/?"
    CLEAR = "/clear"
    HISTORY = "/history"
    SHOW = "/show"
    EXIT = "/exit"


def create_cli_catalog(
    toolkit: str | None = None,
    show_toolkits: bool = False,
) -> ToolCatalog:
    """
    Load toolkits from the python environment.
    """
    if toolkit:
        toolkit = toolkit.lower().replace("-", "_")
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


def compute_base_url(
    force_tls: bool,
    force_no_tls: bool,
    host: str,
    port: int | None,
) -> str:
    """
    Compute the base URL for the Arcade Engine from the provided overrides.

    Treats 127.0.0.1 and 0.0.0.0 as aliases for localhost.

    force_no_tls takes precedence over force_tls. For example, if both are set to True,
    the resulting URL will use http.

    The port is included in the URL unless the host is a fully qualified domain name
    (excluding IP addresses) and no port is specified. Handles IPv4, IPv6, IDNs, and
    hostnames with underscores.

    This property exists to provide a consistent and correctly formatted URL for
    connecting to the Arcade Engine, taking into account various configuration
    options and edge cases. It ensures that:

    1. The correct protocol (http/https) is used based on the TLS setting.
    2. IPv4 and IPv6 addresses are properly formatted.
    3. Internationalized Domain Names (IDNs) are correctly encoded.
    4. Fully Qualified Domain Names (FQDNs) are identified and handled appropriately.
    5. Ports are included when necessary, respecting common conventions for FQDNs.
    6. Hostnames with underscores (common in development environments) are supported.
    7. Pre-existing port specifications in the host are respected.

    The resulting URL is always suffixed with api_version to specify the API version.

    Returns:
        str: The fully constructed URL for the Arcade Engine.
    """
    # "Use 127.0.0.1" and "0.0.0.0" as aliases for "localhost"
    host = LOCALHOST if host in ["127.0.0.1", "0.0.0.0"] else host  # noqa: S104

    # Determine TLS setting based on input flags
    if force_no_tls:
        is_tls = False
    elif force_tls:
        is_tls = True
    else:
        is_tls = host != LOCALHOST

    # "localhost" defaults to dev port if not specified
    if host == LOCALHOST and port is None:
        port = 9099

    protocol = "https" if is_tls else "http"

    # Handle potential IDNs
    try:
        encoded_host = idna.encode(host).decode("ascii")
    except idna.IDNAError:
        encoded_host = host

    # Check if the host is a valid IP address (IPv4 or IPv6)
    try:
        ipaddress.ip_address(encoded_host)
        is_ip = True
    except ValueError:
        is_ip = False

    # Parse the host, handling potential IPv6 addresses
    host_for_parsing = f"[{encoded_host}]" if is_ip and ":" in encoded_host else encoded_host
    parsed_host = urlparse(f"//{host_for_parsing}")

    # Check if the host is a fully qualified domain name (excluding IP addresses)
    is_fqdn = "." in parsed_host.netloc and not is_ip and "_" not in parsed_host.netloc

    # Handle hosts that might already include a port
    if ":" in parsed_host.netloc and not is_ip:
        host, existing_port = parsed_host.netloc.rsplit(":", 1)
        if existing_port.isdigit():
            return f"{protocol}://{parsed_host.netloc}"

    if is_fqdn and port is None:
        return f"{protocol}://{encoded_host}"
    elif port is not None:
        return f"{protocol}://{encoded_host}:{port}"
    else:
        return f"{protocol}://{encoded_host}"


def compute_login_url(host: str, state: str, port: int | None) -> str:
    """
    Compute the full URL for the CLI login endpoint.
    """
    callback_uri = f"http://{LOCALHOST}:9905/callback"
    params = urlencode({"callback_uri": callback_uri, "state": state})

    port = port if port else 8000

    login_base_url = (
        f"http://{LOCALHOST}:{port}"
        if host in [LOCALHOST, "127.0.0.1", "0.0.0.0"]  # noqa: S104
        else f"https://{host}"
    )
    endpoint = "/api/v1/auth/cli_login"

    return f"{login_base_url}{endpoint}?{params}"


def get_tools_from_engine(
    host: str,
    port: int | None = None,
    force_tls: bool = False,
    force_no_tls: bool = False,
    toolkit: str | None = None,
) -> list[ToolDefinition]:
    config = validate_and_get_config()
    base_url = compute_base_url(force_tls, force_no_tls, host, port)
    client = Arcade(api_key=config.api.key, base_url=base_url)

    tools = []
    try:
        page_iterator = client.tools.list(toolkit=toolkit or NOT_GIVEN)
        for tool in page_iterator:
            try:
                tools.append(ToolDefinition.model_validate(tool.model_dump()))
            except ValidationError:
                # Skip listing tools that aren't valid ToolDefinitions
                continue
    except APIConnectionError:
        console.print(
            f"❌ Can't connect to Arcade Engine at {base_url}. (Is it running?)", style="bold red"
        )

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
    validate_api: bool = True,
    validate_user: bool = True,
) -> Config:
    """
    Validates the configuration, user, and returns the Config object
    """
    from arcade_core.config import config

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
        if tool_authorization.url:
            authorization_url = str(tool_authorization.url)
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
                id=cast(str, auth_response.id),
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
        eval_files = [f for f in directory_path.rglob("eval_*.py") if f.is_file()]
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


def get_user_input() -> str:
    """
    Get input from the user, handling multi-line input.
    """
    MULTI_LINE_PROMPT = '"""'
    user_input = input()
    # Handle multi-line input
    if user_input.startswith(MULTI_LINE_PROMPT):
        user_input = user_input[len(MULTI_LINE_PROMPT) :]

        while not user_input.endswith(MULTI_LINE_PROMPT):
            line = input()
            if not line:
                print()
            user_input += "\n" + line

        user_input = user_input.rstrip(MULTI_LINE_PROMPT)
    else:
        # Handle single-line input
        while not user_input.strip():
            user_input = input()

    return user_input.strip()


def display_chat_help() -> None:
    """Display the help message for arcade chat."""
    help_message = dedent(f"""\
        [default]
        Available Commands:
          {ChatCommand.SHOW.value:<13} Show all available tools
          {ChatCommand.HISTORY.value:<13} Show the chat history
          {ChatCommand.CLEAR.value:<13} Clear the chat history
          {ChatCommand.EXIT.value:<13} Exit the chat
          {ChatCommand.HELP_ALT.value}, {ChatCommand.HELP.value:<9} Help for a command

        Surround in \"\"\" for multi-line messages[/default]
    """)
    console.print(help_message)


def handle_user_command(
    user_input: str,
    history: list,
    host: str,
    port: int,
    force_tls: bool,
    force_no_tls: bool,
    show: Callable,
) -> bool:
    """
    Handle user commands during `arcade chat` and return True if a command was processed, otherwise False.
    """
    if user_input in [ChatCommand.HELP, ChatCommand.HELP_ALT]:
        display_chat_help()
        return True
    elif user_input == ChatCommand.EXIT:
        raise KeyboardInterrupt
    elif user_input == ChatCommand.HISTORY:
        console.print(history)
        return True
    elif user_input == ChatCommand.CLEAR:
        console.print("Chat history cleared.", style="bold green")
        history.clear()
        return True
    elif user_input == ChatCommand.SHOW:
        show(
            toolkit=None,
            tool=None,
            host=host,
            local=False,
            port=port,
            force_tls=force_tls,
            force_no_tls=force_no_tls,
            debug=False,
        )
        return True
    return False


def parse_user_command(user_input: str) -> ChatCommand | None:
    """
    Parse the user command and return the corresponding ChatCommand enum.
    Returns None if the input is not a valid chat command.
    """
    try:
        return ChatCommand(user_input)
    except ValueError:
        return None


def version_callback(value: bool) -> None:
    """Callback implementation for the `arcade --version`.
    Prints the version of Arcade and exit.
    """
    if value:
        version = metadata.version("arcade-ai")
        console.print(f"[bold]Arcade CLI[/bold] (version {version})")
        exit()


def get_today_context() -> str:
    today = datetime.now().strftime("%Y-%m-%d")
    day_of_week = datetime.now().strftime("%A")
    return f"Today is {today}, {day_of_week}."


def discover_toolkits() -> list[Toolkit]:
    """Return all Arcade toolkits installed in the active Python environment.

    Raises:
        RuntimeError: If no toolkits are found, mirroring the behaviour of Toolkit discovery elsewhere.
    """
    toolkits = Toolkit.find_all_arcade_toolkits()
    if not toolkits:
        raise RuntimeError("No toolkits found in Python environment.")
    return toolkits


def build_tool_catalog(toolkits: list[Toolkit]) -> ToolCatalog:
    """Construct a ``ToolCatalog`` populated with *toolkits*.


    Args:
        toolkits: Toolkits to register in the catalog.

    Returns:
        ToolCatalog
    """
    catalog = ToolCatalog()
    for tk in toolkits:
        catalog.add_toolkit(tk)
    return catalog


def _parse_line(line: str) -> tuple[str, str] | None:
    """
    Return (key, value) if the line looks like KEY=VALUE, else None.
    Handles quotes and escaped chars via shlex.
    """
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, raw_val = line.split("=", 1)
    key = key.strip()
    raw_val = raw_val.strip()

    # Use shlex to handle "quoted strings with # hash" etc.
    try:
        value = shlex.split(raw_val)[0] if raw_val else ""
    except ValueError:
        # Fallback: naked value without shlex parsing
        value = raw_val

    return key, value


def load_dotenv(path: str | Path, *, override: bool = False) -> dict[str, str]:
    """
    Load variables from *path* into os.environ.

    Args:
        path: .env file path
        override: replace existing env vars if True

    Returns:
        The mapping of vars that were added/updated.
    """
    path = Path(path).expanduser()
    if not path.is_file():
        return {}

    loaded: dict[str, str] = {}

    for raw in path.read_text().splitlines():
        parsed = _parse_line(raw.strip())
        if parsed is None:
            continue
        k, v = parsed
        if override or k not in os.environ:
            os.environ[k] = v
            loaded[k] = v

    return loaded


def require_dependency(
    package_name: str,
    command_name: str,
    install_command: str,
) -> None:
    """
    Display a helpful error message if the required dependency is missing.

    Args:
        package_name: The name of the package to import (e.g., 'arcade_serve')
        command_name: The command that requires the package (e.g., 'serve')
        install_command: The command to install the package (e.g., "pip install 'arcade-ai[evals]'")
    """
    try:
        importlib.import_module(package_name.replace("-", "_"))
    except ImportError:
        console.print(
            f"❌ The '{package_name}' package is required to run the '{command_name}' command but is not installed.",
            style="bold red",
        )
        console.print(
            f"To install it, run the following command:\n* [green]{install_command}[/green]",
            style="bold",
        )
        raise typer.Exit(code=1)
