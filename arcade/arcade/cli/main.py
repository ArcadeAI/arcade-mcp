import asyncio
import os
import readline
import threading
import uuid
import webbrowser
from typing import Any, Optional
from urllib.parse import urlencode

import typer
from arcadepy import Arcade
from arcadepy.types import AuthorizationResponse
from openai import OpenAI, OpenAIError
from rich.console import Console
from rich.markup import escape
from rich.text import Text

from arcade.cli.authn import LocalAuthCallbackServer, check_existing_login
from arcade.cli.constants import DEFAULT_CLOUD_HOST, DEFAULT_ENGINE_HOST
from arcade.cli.display import (
    display_arcade_chat_header,
    display_eval_results,
    display_tool_details,
    display_tool_messages,
    display_tools_table,
)
from arcade.cli.launcher import start_servers
from arcade.cli.utils import (
    OrderCommands,
    compute_base_url,
    create_cli_catalog,
    delete_deprecated_config_file,
    get_eval_files,
    get_tools_from_engine,
    handle_chat_interaction,
    handle_tool_authorization,
    is_authorization_pending,
    load_eval_suites,
    log_engine_health,
    validate_and_get_config,
)

cli = typer.Typer(
    cls=OrderCommands,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)
console = Console()


@cli.command(help="Log in to Arcade Cloud", rich_help_panel="User")
def login(
    host: str = typer.Option(
        DEFAULT_CLOUD_HOST,
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
        if not webbrowser.open(login_url):
            console.print(
                f"If a browser doesn't open automatically, copy this URL and paste it into your browser: {login_url}",
                style="dim",
            )

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
    delete_deprecated_config_file()

    # If ~/.arcade/credentials.yaml exists, delete it
    config_file_path = os.path.expanduser("~/.arcade/credentials.yaml")
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
    help="Show the installed toolkits or details of a specific tool",
    rich_help_panel="Tool Development",
)
def show(
    toolkit: Optional[str] = typer.Option(
        None, "-T", "--toolkit", help="The toolkit to show the tools of"
    ),
    tool: Optional[str] = typer.Option(
        None, "-t", "--tool", help="The specific tool to show details for"
    ),
    host: str = typer.Option(
        DEFAULT_ENGINE_HOST,
        "-h",
        "--host",
        help="The Arcade Engine address to send chat requests to.",
    ),
    port: Optional[int] = typer.Option(
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
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Show the available toolkits or detailed information about a specific tool.
    """
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104
    try:
        if host in local_hosts:
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


@cli.command(help="Start Arcade Chat in the terminal", rich_help_panel="Launch")
def chat(
    model: str = typer.Option("gpt-4o", "-m", help="The model to use for prediction."),
    stream: bool = typer.Option(
        False, "-s", "--stream", is_flag=True, help="Stream the tool output."
    ),
    prompt: str = typer.Option(None, "--prompt", help="The system prompt to use for the chat."),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
    host: str = typer.Option(
        DEFAULT_ENGINE_HOST,
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
    config = validate_and_get_config()
    base_url = compute_base_url(force_tls, force_no_tls, host, port)

    client = Arcade(api_key=config.api.key, base_url=base_url)
    user_email = config.user.email if config.user else None

    try:
        # start messages conversation
        history: list[dict[str, Any]] = []

        if prompt:
            history.append({"role": "system", "content": prompt})

        display_arcade_chat_header(base_url, stream)

        # Try to hit /health endpoint on engine and warn if it is down
        log_engine_health(client)

        while True:
            console.print(f"\n[magenta][bold]User[/bold] ({user_email}):[/magenta] ")

            # Use input() instead of console.input() to leverage readline history
            user_input = input()

            # Add the input to history
            readline.add_history(user_input)

            history.append({"role": "user", "content": user_input})

            try:
                # TODO fixup configuration to remove this + "/v1" workaround
                openai_client = OpenAI(api_key=config.api.key, base_url=base_url + "/v1")
                chat_result = handle_chat_interaction(
                    openai_client, model, history, user_email, stream
                )

                history = chat_result.history
                tool_messages = chat_result.tool_messages
                tool_authorization = chat_result.tool_authorization

                # wait for tool authorizations to complete, if any
                if tool_authorization and is_authorization_pending(tool_authorization):
                    chat_result = handle_tool_authorization(
                        client,
                        AuthorizationResponse.model_validate(tool_authorization),
                        history,
                        openai_client,
                        model,
                        user_email,
                        stream,
                    )
                    history = chat_result.history
                    tool_messages = chat_result.tool_messages

            except OpenAIError as e:
                console.print(f"❌ Arcade Chat failed with error: {e!s}", style="bold red")
                continue
            if debug:
                display_tool_messages(tool_messages)

    except KeyboardInterrupt:
        console.print("Chat stopped by user.", style="bold blue")
        typer.Exit()

    except RuntimeError as e:
        error_message = f"❌ Failed to run tool{': ' + escape(str(e)) if str(e) else ''}"
        console.print(error_message, style="bold red")
        raise typer.Exit()


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
        "gpt-4o",
        "--models",
        "-m",
        help="The models to use for evaluation (default: gpt-4o)",
    ),
    host: str = typer.Option(
        DEFAULT_ENGINE_HOST,
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
    config = validate_and_get_config()
    base_url = compute_base_url(force_tls, force_no_tls, host, port)

    models_list = models.split(",")  # Use 'models_list' to avoid shadowing

    eval_files = get_eval_files(directory)
    if not eval_files:
        return

    if show_details:
        console.print(
            Text.assemble(
                ("\nRunning evaluations against Arcade Engine at ", "bold"),
                (base_url, "bold blue"),
            )
        )

    # Try to hit /health endpoint on engine and warn if it is down
    with Arcade(api_key=config.api.key, base_url=base_url) as client:
        log_engine_health(client)

    # Use the new function to load eval suites
    eval_suites = load_eval_suites(eval_files)

    if not eval_suites:
        console.print("No evaluation suites to run.", style="bold yellow")
        return

    if show_details:
        suite_label = "suite" if len(eval_suites) == 1 else "suites"
        console.print(
            f"\nFound {len(eval_suites)} {suite_label} in the evaluation files.",
            style="bold",
        )

    async def run_evaluations() -> None:
        all_evaluations = []
        tasks = []
        for suite_func in eval_suites:
            console.print(
                Text.assemble(
                    ("Running evaluations in ", "bold"),
                    (suite_func.__name__, "bold blue"),
                )
            )
            for model in models_list:
                task = asyncio.create_task(
                    suite_func(
                        config=config,
                        base_url=base_url,
                        model=model,
                        max_concurrency=max_concurrent,
                    )
                )
                tasks.append(task)

        # TODO add a progress bar here
        # TODO error handling on each eval
        # Wait for all suite functions to complete
        results = await asyncio.gather(*tasks)
        all_evaluations.extend(results)
        display_eval_results(all_evaluations, show_details=show_details)

    asyncio.run(run_evaluations())


@cli.command(help="Launch Arcade AI locally for tool dev", rich_help_panel="Launch")
def dev(
    host: str = typer.Option("127.0.0.1", help="Host for the actor server.", show_default=True),
    port: int = typer.Option(
        8002, "-p", "--port", help="Port for the actor server.", show_default=True
    ),
    engine_config: str = typer.Option(
        None, "-c", "--config", help="Path to the engine configuration file."
    ),
    env_file: str = typer.Option(
        None, "-e", "--env-file", help="Path to the environment variables file."
    ),
    debug: bool = typer.Option(False, "-d", "--debug", help="Show debug information"),
) -> None:
    """
    Start both the actor and engine servers.
    """
    try:
        start_servers(host, port, engine_config, engine_env=env_file, debug=debug)
    except Exception as e:
        error_message = f"❌ Failed to start servers: {escape(str(e))}"
        console.print(error_message, style="bold red")
        typer.Exit(code=1)


@cli.command(help="Start a local Arcade Actor server", rich_help_panel="Launch", hidden=True)
def actorup(
    host: str = typer.Option(
        "127.0.0.1",
        help="Host for the app, from settings by default.",
        show_default=True,
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
    otel_enable: bool = typer.Option(
        False, "--otel-enable", help="Send logs to OpenTelemetry", show_default=True
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Starts the actor with host, port, and reload options. Uses
    Uvicorn as ASGI actor. Parameters allow runtime configuration.
    """
    from arcade.cli.serve import serve_default_actor

    try:
        serve_default_actor(
            host, port, disable_auth=disable_auth, enable_otel=otel_enable, debug=debug
        )
    except KeyboardInterrupt:
        typer.Exit()
    except Exception as e:
        error_message = f"❌ Failed to start Arcade Actor: {escape(str(e))}"
        console.print(error_message, style="bold red")
        typer.Exit(code=1)
