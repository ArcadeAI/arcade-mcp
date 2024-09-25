import importlib.util
import os
import readline
import threading
import uuid
import webbrowser
from typing import Any, Optional
from urllib.parse import urlencode

import typer
from openai import OpenAIError
from rich.console import Console
from rich.markup import escape
from rich.table import Table
from rich.text import Text

from arcade.cli.authn import LocalAuthCallbackServer, check_existing_login
from arcade.cli.launcher import start_servers
from arcade.cli.utils import (
    OrderCommands,
    apply_config_overrides,
    create_cli_catalog,
    display_eval_results,
    display_tool_messages,
    handle_chat_interaction,
    is_authorization_pending,
    validate_and_get_config,
    wait_for_authorization_completion,
)
from arcade.client import Arcade
from arcade.client.errors import EngineNotHealthyError, EngineOfflineError
from arcade.core.config_model import Config

cli = typer.Typer(
    cls=OrderCommands,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)
console = Console()


def _get_config_with_overrides(
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


@cli.command(help="Log in to Arcade Cloud", rich_help_panel="User")
def login(
    host: str = typer.Option(
        "cloud.arcade-ai.com",
        "-h",
        "--host",
        help="The Arcade Cloud host to log in to.",
    ),
) -> None:
    """
    Logs the user into Arcade Cloud.
    """

    if check_existing_login():
        return

    # Start the HTTP server in a new thread
    state = str(uuid.uuid4())
    auth_server = LocalAuthCallbackServer(state)
    server_thread = threading.Thread(target=auth_server.run_server)
    server_thread.start()

    try:
        # Open the browser for user login
        callback_uri = "http://localhost:9905/callback"
        params = urlencode({"callback_uri": callback_uri, "state": state})
        login_url = f"https://{host}/api/v1/auth/cli_login?{params}"
        console.print("Opening a browser to log you in...")
        webbrowser.open(login_url)

        # Wait for the server thread to finish
        server_thread.join()
    except KeyboardInterrupt:
        auth_server.shutdown_server()
    finally:
        if server_thread.is_alive():
            server_thread.join()  # Ensure the server thread completes and cleans up


@cli.command(help="Log out of Arcade Cloud", rich_help_panel="User")
def logout() -> None:
    """
    Logs the user out of Arcade Cloud.
    """

    # If ~/.arcade/arcade.toml exists, delete it
    config_file_path = os.path.expanduser("~/.arcade/arcade.toml")
    if os.path.exists(config_file_path):
        os.remove(config_file_path)
        console.print("You're now logged out.", style="bold")
    else:
        console.print("You're not logged in.", style="bold red")


@cli.command(help="Create a new toolkit package directory", rich_help_panel="Tool Development")
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


@cli.command(
    help="Show the installed toolkits",
    rich_help_panel="Tool Development",
)
def show(
    toolkit: Optional[str] = typer.Option(
        None, "-t", "--toolkit", help="The toolkit to show the tools of"
    ),
    actor: Optional[str] = typer.Option(None, help="A running actor address to list tools from"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Show the available tools in an actor or toolkit
    """

    try:
        catalog = create_cli_catalog(toolkit=toolkit)

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
        if debug:
            raise
        error_message = f"❌ Failed to List tools: {escape(str(e))}"
        console.print(error_message, style="bold red")


@cli.command(help="Start Arcade Chat in the terminal", rich_help_panel="Launch")
def chat(
    model: str = typer.Option("gpt-4o", "-m", help="The model to use for prediction."),
    stream: bool = typer.Option(
        False, "-s", "--stream", is_flag=True, help="Stream the tool output."
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
    host: str = typer.Option(
        None,
        "-h",
        "--host",
        help="The Arcade Engine address to send chat requests to.",
    ),
    port: int = typer.Option(
        None,
        "-p",
        "--port",
        help="The port of the Arcade Engine.",
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine. If not specified, the connection will use TLS if the engine URL uses a 'https' scheme.",
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
    ),
) -> None:
    """
    Chat with a language model.
    """
    config = _get_config_with_overrides(force_tls, force_no_tls, host, port)

    client = Arcade(api_key=config.api.key, base_url=config.engine_url)
    user_email = config.user.email if config.user else None
    user_attribution = f"({user_email})" if user_email else ""

    try:
        # start messages conversation
        history: list[dict[str, Any]] = []

        chat_header = Text.assemble(
            "\n",
            (
                "=== Arcade AI Chat ===",
                "bold magenta underline",
            ),
            "\n",
            "\n",
            "Chatting with Arcade Engine at ",
            (
                config.engine_url,
                "bold blue",
            ),
        )
        if stream:
            chat_header.append(" (streaming)")
        console.print(chat_header)

        # Try to hit /health endpoint on engine and warn if it is down
        log_engine_health(client)

        while True:
            console.print(f"\n[magenta][bold]User[/bold] {user_attribution}:[/magenta] ")

            # Use input() instead of console.input() to leverage readline history
            user_input = input()

            # Add the input to history
            readline.add_history(user_input)

            history.append({"role": "user", "content": user_input})

            try:
                chat_result = handle_chat_interaction(client, model, history, user_email, stream)
            except OpenAIError as e:
                console.print(f"❌ Arcade Chat failed with error: {e!s}", style="bold red")
                continue

            history = chat_result.history
            tool_messages = chat_result.tool_messages
            tool_authorization = chat_result.tool_authorization

            # wait for tool authorizations to complete, if any
            if is_authorization_pending(tool_authorization):
                with console.status("Waiting for you to authorize the action...", spinner="dots"):
                    wait_for_authorization_completion(client, tool_authorization)
                # re-run the chat request now that authorization is complete
                try:
                    chat_result = handle_chat_interaction(
                        client, model, history, user_email, stream
                    )
                except OpenAIError as e:
                    console.print(f"❌ Arcade Chat failed with error: {e!s}", style="bold red")
                    continue

                history = chat_result.history
                tool_messages = chat_result.tool_messages

            if debug:
                display_tool_messages(tool_messages)

    except KeyboardInterrupt:
        console.print("Chat stopped by user.", style="bold blue")
        typer.Exit()

    except RuntimeError as e:
        error_message = f"❌ Failed to run tool{': ' + escape(str(e)) if str(e) else ''}"
        console.print(error_message, style="bold red")
        raise typer.Exit()


@cli.command(help="Start a local Arcade Actor server", rich_help_panel="Launch")
def dev(
    host: str = typer.Option(
        "127.0.0.1", help="Host for the app, from settings by default.", show_default=True
    ),
    port: int = typer.Option(
        "8002", "-p", "--port", help="Port for the app, defaults to ", show_default=True
    ),
    disable_auth: bool = typer.Option(
        False,
        "--no-auth",
        help="Disable authentication for the actor. Not recommended for production.",
        show_default=True,
    ),
) -> None:
    """
    Starts the actor with host, port, and reload options. Uses
    Uvicorn as ASGI actor. Parameters allow runtime configuration.
    """
    from arcade.cli.serve import serve_default_actor

    try:
        serve_default_actor(host, port, disable_auth)
    except KeyboardInterrupt:
        typer.Exit()
    except Exception as e:
        error_message = f"❌ Failed to start Arcade Actor: {escape(str(e))}"
        console.print(error_message, style="bold red")
        raise typer.Exit(code=1)


@cli.command(help="Show/edit the local Arcade configuration", rich_help_panel="User")
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
    config = validate_and_get_config()

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


def log_engine_health(client: Arcade) -> None:
    try:
        client.health.check()

    except EngineNotHealthyError as e:
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
    except EngineOfflineError:
        console.print(
            "⚠️ Warning: Arcade Engine was unreachable. (Is it running?)",
            style="bold yellow",
        )


def display_config_as_table(config) -> None:  # type: ignore[no-untyped-def]
    """
    Display the configuration details as a table using Rich library.
    """
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Section")
    table.add_column("Name")
    table.add_column("Value")

    for section_name in config.model_dump():
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


@cli.command(help="Run tool calling evaluations", rich_help_panel="Tool Development")
def evals(
    directory: str = typer.Argument(".", help="Directory containing evaluation files"),
    show_details: bool = typer.Option(False, "--details", "-d", help="Show detailed results"),
    max_concurrent: int = typer.Option(
        1,
        "--max-concurrent",
        "-c",
        help="Maximum number of concurrent evaluations (default: 1)",
    ),
    models: str = typer.Option(
        "gpt-4o", "--models", "-m", help="The models to use for evaluation (default: gpt-4o)"
    ),
    host: str = typer.Option(
        None,
        "-h",
        "--host",
        help="The Arcade Engine address to send chat requests to.",
    ),
    port: int = typer.Option(
        None,
        "-p",
        "--port",
        help="The port of the Arcade Engine.",
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine. If not specified, the connection will use TLS if the engine URL uses a 'https' scheme.",
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
    ),
) -> None:
    """
    Find all files starting with 'eval_' in the given directory,
    execute any functions decorated with @tool_eval, and display the results.
    """
    config = _get_config_with_overrides(force_tls, force_no_tls, host, port)

    models = models.split(",")  # type: ignore[assignment]
    eval_files = [f for f in os.listdir(directory) if f.startswith("eval_") and f.endswith(".py")]

    if not eval_files:
        console.print("No evaluation files found.", style="bold yellow")
        return

    if show_details:
        console.print(
            Text.assemble(
                ("\nRunning evaluations against Arcade Engine at ", "bold"),
                (config.engine_url, "bold blue"),
            )
        )

    # Try to hit /health endpoint on engine and warn if it is down
    client = Arcade(api_key=config.api.key, base_url=config.engine_url)
    log_engine_health(client)

    for file in eval_files:
        file_path = os.path.join(directory, file)
        module_name = file[:-3]  # Remove .py extension

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            console.print(f"Failed to load {file}", style="bold red")
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]

        eval_suites = [
            obj
            for name, obj in module.__dict__.items()
            if callable(obj) and hasattr(obj, "__tool_eval__")
        ]

        if not eval_suites:
            console.print(f"No @tool_eval functions found in {file}", style="bold yellow")
            continue

        if show_details:
            suite_label = "suite" if len(eval_suites) == 1 else "suites"
            console.print(f"\nFound {len(eval_suites)} {suite_label} in {file}", style="bold")

        for suite_func in eval_suites:
            console.print(
                Text.assemble(
                    ("\nRunning evaluations in ", "bold"),
                    (suite_func.__name__, "bold blue"),
                )
            )
            results = suite_func(config=config, models=models, max_concurrency=max_concurrent)
            display_eval_results(results, show_details=show_details)


@cli.command(help="Start an Arcade Cluster instance", rich_help_panel="Launch")
def up(
    host: str = typer.Option("127.0.0.1", help="Host for the actor server.", show_default=True),
    port: int = typer.Option(
        8002, "-p", "--port", help="Port for the actor server.", show_default=True
    ),
    engine_config: str = typer.Option(
        None, "-c", "--config", help="Path to the engine configuration file."
    ),
) -> None:
    """
    Start both the actor and engine servers.
    """
    try:
        # TODO: pass Engine env vars from here
        start_servers(host, port, engine_config)
    except Exception as e:
        error_message = f"❌ Failed to start servers: {escape(str(e))}"
        console.print(error_message, style="bold red")
        typer.Exit(code=1)
