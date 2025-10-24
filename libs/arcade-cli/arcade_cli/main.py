import asyncio
import os
import subprocess
import sys
import threading
import uuid
import webbrowser
from pathlib import Path
from typing import Optional

import click
import typer
from arcade_core.constants import CREDENTIALS_FILE_PATH
from arcadepy import Arcade
from rich.console import Console
from rich.text import Text
from tqdm import tqdm

from arcade_cli.authn import LocalAuthCallbackServer, check_existing_login
from arcade_cli.constants import (
    PROD_CLOUD_HOST,
    PROD_ENGINE_HOST,
)
from arcade_cli.display import (
    display_eval_results,
)
from arcade_cli.secret import app as secret_app
from arcade_cli.server import app as server_app
from arcade_cli.show import show_logic
from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import (
    Provider,
    compute_base_url,
    compute_login_url,
    get_eval_files,
    handle_cli_error,
    load_eval_suites,
    log_engine_health,
    require_dependency,
    resolve_provider_api_key,
    validate_and_get_config,
    version_callback,
)

cli = TrackedTyper(
    cls=TrackedTyperGroup,
    add_completion=False,
    no_args_is_help=True,
    pretty_exceptions_enable=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
    rich_markup_mode="markdown",
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Arcade CLI - Build, deploy, and manage MCP servers and AI tools. Create new projects, run servers with multiple transports, configure clients, and deploy to Arcade Cloud.",
    epilog="Pro tip: use --help after any command to see command-specific options.",
)


cli.add_typer(
    server_app,
    name="server",
    help="Manage deployments of tool servers (logs, list, etc)",
    rich_help_panel="Manage",
)

cli.add_typer(
    secret_app,
    name="secret",
    help="Manage tool secrets in the cloud (set, unset, list)",
    rich_help_panel="Manage",
)


console = Console()


@cli.command(help="Log in to Arcade Cloud", rich_help_panel="User")
def login(
    host: str = typer.Option(
        PROD_CLOUD_HOST,
        "-h",
        "--host",
        help="The Arcade Cloud host to log in to.",
    ),
    port: Optional[int] = typer.Option(
        None,
        "-p",
        "--port",
        help="The port of the Arcade Cloud host (if running locally).",
    ),
    callback_host: str = typer.Option(
        None,
        "--callback-host",
        help="The host to use to complete the auth flow - this should be the same as the host that the CLI is running on. Include the port if needed.",
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Logs the user into Arcade Cloud.
    """

    if check_existing_login():
        console.print("\nTo log out and delete your locally-stored credentials, use ", end="")
        console.print("arcade logout", style="bold green", end="")
        console.print(".\n")
        return

    # Start the HTTP server in a new thread
    state = str(uuid.uuid4())
    auth_server = LocalAuthCallbackServer(state)
    server_thread = threading.Thread(target=auth_server.run_server)
    server_thread.start()

    try:
        # Open the browser for user login
        login_url = compute_login_url(host, state, port, callback_host)

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
    except Exception as e:
        handle_cli_error("Login failed", e, debug)
    finally:
        if server_thread.is_alive():
            server_thread.join()  # Ensure the server thread completes and cleans up


@cli.command(help="Log out of Arcade Cloud", rich_help_panel="User")
def logout(
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Logs the user out of Arcade Cloud.
    """
    try:
        # If the credentials file exists, delete it
        if os.path.exists(CREDENTIALS_FILE_PATH):
            os.remove(CREDENTIALS_FILE_PATH)
            console.print("You're now logged out.", style="bold")
        else:
            console.print("You're not logged in.", style="bold red")
    except Exception as e:
        handle_cli_error("Logout failed", e, debug)


@cli.command(
    help="Create a new server package directory. Example usage: `arcade new my_mcp_server`",
    rich_help_panel="Build",
)
def new(
    server_name: str = typer.Argument(
        help="The name of the server to create",
        metavar="SERVER_NAME",
    ),
    directory: str = typer.Option(os.getcwd(), "--dir", help="tools directory path"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
    full: bool = typer.Option(
        False,
        "--full",
        "-f",
        help="Create a starter MCP server (pyproject.toml, server.py, .env.example)",
    ),
) -> None:
    """
    Creates a new MCP server with the given name
    """
    from arcade_cli.new import create_new_toolkit, create_new_toolkit_minimal

    try:
        if not full:
            create_new_toolkit_minimal(directory, server_name)
        else:
            create_new_toolkit(directory, server_name)
    except Exception as e:
        handle_cli_error("Failed to create new server", e, debug)


@cli.command(
    name="mcp",
    help="Run MCP servers with different transports",
    rich_help_panel="Run",
)
def mcp(
    transport: str = typer.Argument("http", help="Transport type: stdio, http"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to (HTTP mode only)"),
    port: int = typer.Option(8000, "--port", help="Port to bind to (HTTP mode only)"),
    tool_package: Optional[str] = typer.Option(
        None,
        "--tool-package",
        "--package",
        "-p",
        help="Specific tool package to load (e.g., 'github' for arcade-github)",
    ),
    discover_installed: bool = typer.Option(
        False, "--discover-installed", "--all", help="Discover all installed arcade tool packages"
    ),
    show_packages: bool = typer.Option(
        False, "--show-packages", help="Show loaded packages during discovery"
    ),
    reload: bool = typer.Option(
        False, "--reload", help="Enable auto-reload on code changes (HTTP mode only)"
    ),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode with verbose logging"),
    otel_enable: bool = typer.Option(
        False, "--otel-enable", help="Send logs to OpenTelemetry", show_default=True
    ),
    env_file: Optional[str] = typer.Option(None, "--env-file", help="Path to environment file"),
    name: Optional[str] = typer.Option(None, "--name", help="Server name"),
    version: Optional[str] = typer.Option(None, "--version", help="Server version"),
    cwd: Optional[str] = typer.Option(None, "--cwd", help="Working directory to run from"),
) -> None:
    """
    Run Arcade MCP Server (passthrough to arcade_mcp_server).

    This command provides a unified CLI experience by passing through
    all arguments to the arcade_mcp_server module.

    Examples:
        arcade mcp stdio
        arcade mcp http --port 8080
        arcade mcp --tool-package github
        arcade mcp --discover-installed --show-packages
    """
    # Build the command to pass through to arcade_mcp_server
    cmd = [sys.executable, "-m", "arcade_mcp_server", transport]

    # Add optional arguments
    cmd.extend(["--host", host])
    cmd.extend(["--port", str(port)])
    if debug:
        cmd.append("--debug")
    if otel_enable:
        cmd.append("--otel-enable")
    if tool_package:
        cmd.extend(["--tool-package", tool_package])
    if discover_installed:
        cmd.append("--discover-installed")
    if show_packages:
        cmd.append("--show-packages")
    if reload:
        cmd.append("--reload")
    if env_file:
        cmd.extend(["--env-file", env_file])
    if name:
        cmd.extend(["--name", name])
    if version:
        cmd.extend(["--version", version])
    if cwd:
        cmd.extend(["--cwd", cwd])

    try:
        # Show what command we're running in debug mode
        if debug:
            console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

        # Execute the command and pass through all output
        result = subprocess.run(cmd, check=False)

        # Exit with the same code as the subprocess
        if result.returncode != 0:
            handle_cli_error("Failed to run MCP server")

    except KeyboardInterrupt:
        console.print("\n[yellow]MCP server gracefully shutdown[/yellow]")
    except FileNotFoundError:
        handle_cli_error(
            "arcade_mcp_server module not found. Make sure arcade-mcp-server is installed"
        )


@cli.command(
    help="Show the installed tools or details of a specific tool",
    rich_help_panel="Build",
)
def show(
    server: Optional[str] = typer.Option(
        None, "-T", "--server", help="The server to show the tools of"
    ),
    tool: Optional[str] = typer.Option(
        None, "-t", "--tool", help="The specific tool to show details for"
    ),
    host: str = typer.Option(
        PROD_ENGINE_HOST,
        "-h",
        "--host",
        help="The Arcade Engine address to show the tools/servers of.",
    ),
    local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="Show the local environment's catalog instead of an Arcade Engine's catalog.",
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
    full: bool = typer.Option(
        False,
        "--full",
        "-f",
        help="Show full server response structure including error, logs, and authorization fields (only applies when used with -t/--tool).",
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Show the available tools or detailed information about a specific tool.
    """
    if full and not tool:
        console.print(
            "⚠️  The -f/--full flag only affects output when used with -t/--tool flag",
            style="bold yellow",
        )

    show_logic(
        toolkit=server,
        tool=tool,
        host=host,
        local=local,
        port=port,
        force_tls=force_tls,
        force_no_tls=force_no_tls,
        worker=full,
        debug=debug,
    )


@cli.command(help="Run tool calling evaluations", rich_help_panel="Build")
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
        help="The models to use for evaluation (default: gpt-4o). Use commas to separate multiple models. All models must belong to the same provider.",
    ),
    provider: Provider = typer.Option(
        Provider.OPENAI,
        "--provider",
        "-p",
        help="The provider of the models to use for evaluation.",
    ),
    provider_api_key: str = typer.Option(
        None,
        "--provider-api-key",
        "-k",
        help="The model provider API key. If not provided, will look for the appropriate environment variable based on the provider (e.g., OPENAI_API_KEY for openai provider), first in the current environment, then in the current working directory's .env file.",
    ),
    debug: bool = typer.Option(False, "--debug", help="Show debug information"),
) -> None:
    """
    Find all files starting with 'eval_' in the given directory,
    execute any functions decorated with @tool_eval, and display the results.
    """
    require_dependency(
        package_name="arcade_evals",
        command_name="evals",
        install_command=r"pip install 'arcade-mcp\[evals]'",
    )
    # Although Evals does not depend on the TDK, some evaluations import the
    # ToolCatalog class from the TDK instead of from arcade_core, so we require
    # the TDK to run the evals CLI command to avoid possible import errors.
    require_dependency(
        package_name="arcade_tdk",
        command_name="evals",
        install_command=r"pip install arcade-tdk",
    )

    models_list = models.split(",")  # Use 'models_list' to avoid shadowing

    # Resolve the API key for the provider
    resolved_api_key = resolve_provider_api_key(provider, provider_api_key)
    if not resolved_api_key:
        provider_env_vars = {
            Provider.OPENAI: "OPENAI_API_KEY",
        }
        env_var_name = provider_env_vars.get(provider, f"{provider.upper()}_API_KEY")
        handle_cli_error(
            f"API key not found for provider '{provider.value}'. "
            f"Please provide it via --provider-api-key,-k argument, set the {env_var_name} environment variable, "
            f"or add it to a .env file in the current directory.",
            should_exit=True,
        )

    eval_files = get_eval_files(directory)
    if not eval_files:
        return

    console.print("\nRunning evaluations", style="bold")

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
                        provider_api_key=resolved_api_key,
                        model=model,
                        max_concurrency=max_concurrent,
                    )
                )
                tasks.append(task)

        # Track progress and results as suite functions complete
        with tqdm(total=len(tasks), desc="Evaluations Progress") as pbar:
            results = []
            for f in asyncio.as_completed(tasks):
                results.append(await f)
                pbar.update(1)

        # TODO error handling on each eval
        all_evaluations.extend(results)
        display_eval_results(all_evaluations, show_details=show_details)

    try:
        asyncio.run(run_evaluations())
    except Exception as e:
        handle_cli_error("Failed to run evaluations", e, debug)


@cli.command(help="Configure MCP clients to connect to your server", rich_help_panel="Manage")
def configure(
    client: str = typer.Argument(
        ...,
        help="The MCP client to configure (claude, cursor, vscode)",
        click_type=click.Choice(["claude", "cursor", "vscode"], case_sensitive=False),
        show_choices=True,
    ),
    entrypoint_file: str = typer.Option(
        "server.py",
        "--entrypoint",
        "-e",
        help="The name of the Python file in the current directory that runs the server. This file must run the server when invoked directly. Only used for stdio servers.",
        rich_help_panel="Stdio Options",
    ),
    transport: str = typer.Option(
        "stdio",
        "--transport",
        "-t",
        help="The transport to use for the MCP server configuration",
        click_type=click.Choice(["stdio", "http"], case_sensitive=False),
        show_choices=True,
    ),
    server_name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Optional name of the server to set in the configuration file (defaults to the name of the current directory)",
        rich_help_panel="Configuration File Options",
    ),
    host: str = typer.Option(
        "local",
        "--host",
        "-h",
        help="The host of the HTTP server to configure. Use 'local' to connect to a local MCP server or 'arcade' to connect to an Arcade Cloud MCP server.",
        click_type=click.Choice(["local", "arcade"], case_sensitive=False),
        show_choices=True,
        rich_help_panel="HTTP Options",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port for local HTTP servers",
        rich_help_panel="HTTP Options",
    ),
    config_path: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        exists=False,
        help="Optional path to a specific MCP client config file (overrides default path)",
        rich_help_panel="Configuration File Options",
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Configure MCP clients to connect to your server.

    The default behavior is to configure the specified client for a local stdio server that
    runs when the server.py file in the current directory is invoked directly.

    Examples:
        arcade configure claude
        arcade configure cursor --transport http --port 8080
        arcade configure vscode --host arcade --entrypoint my_server.py --config .vscode/mcp.json
        arcade configure claude --host local --name my_server_name
    """
    from arcade_cli.configure import configure_client

    try:
        configure_client(
            client=client,
            entrypoint_file=entrypoint_file,
            server_name=server_name,
            transport=transport,
            host=host,
            port=port,
            config_path=config_path,
        )
    except Exception as e:
        handle_cli_error(f"Failed to configure {client}", e, debug)


@cli.command(
    name="deploy",
    help="Deploy MCP servers to Arcade",
    rich_help_panel="Run",
)
def deploy(
    entrypoint: str = typer.Option(
        "server.py",
        "--entrypoint",
        "-e",
        help="Relative path to the Python file that runs the MCPApp instance (relative to project root). This file must execute the `run()` method on your `MCPApp` instance when invoked directly.",
    ),
    skip_validate: bool = typer.Option(
        False,
        "--skip-validate",
        "--yolo",
        help="Skip running the server locally for health/metadata checks. "
        "When set, you must provide `--server-name` and `--server-version`. "
        "Secret handling is controlled by `--secrets`.",
        rich_help_panel="Advanced",
    ),
    server_name: Optional[str] = typer.Option(
        None,
        "--server-name",
        "-n",
        help="Explicit server name to use when `--skip-validate` is set. Only used when `--skip-validate` is set.",
        rich_help_panel="Advanced",
    ),
    server_version: Optional[str] = typer.Option(
        None,
        "--server-version",
        "-v",
        help="Explicit server version to use when `--skip-validate` is set. Only used when `--skip-validate` is set.",
        rich_help_panel="Advanced",
    ),
    secrets: str = typer.Option(
        "auto",
        "--secrets",
        "-s",
        help=(
            "How to upsert secrets before deploy:\n"
            "  `auto` (default): During validation, discover required secret KEYS and upsert only those. "
            "If `--skip-validate` is set, `auto` becomes `skip`.\n"
            "  `all`: Upsert every key/value pair from your server's .env file regardless of what the server needs.\n"
            "  `skip`: Do not upsert any secrets (assumes they are already present in Arcade)."
        ),
        show_choices=True,
        rich_help_panel="Advanced",
        click_type=click.Choice(["auto", "all", "skip"], case_sensitive=False),
    ),
    host: str = typer.Option(
        PROD_ENGINE_HOST,
        "--host",
        "-h",
        help="The Arcade Engine host to deploy to",
        hidden=True,
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        "-p",
        help="The port of the Arcade Engine",
        hidden=True,
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Force TLS for the connection to the Arcade Engine",
        hidden=True,
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Disable TLS for the connection to the Arcade Engine",
        hidden=True,
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Deploy an MCP server directly to Arcade Engine.

    This command should be run from the root of your MCP server package
    (the directory containing pyproject.toml).

    Examples:
        cd my_mcp_server/
        arcade deploy
        arcade deploy --entrypoint src/server.py
        arcade deploy --skip-validate --server-name my_server_name --server-version 1.0.0
    """
    from arcade_cli.deploy import deploy_server_logic

    if skip_validate and not (server_name and server_version):
        handle_cli_error(
            "When --skip-validate is set, you must provide --server-name and --server-version.",
            should_exit=True,
        )
    if skip_validate and secrets == "auto":
        secrets = "skip"

    try:
        deploy_server_logic(
            entrypoint=entrypoint,
            skip_validate=skip_validate,
            server_name=server_name,
            server_version=server_version,
            secrets=secrets,
            host=host,
            port=port,
            force_tls=force_tls,
            force_no_tls=force_no_tls,
            debug=debug,
        )
    except Exception as e:
        handle_cli_error("Failed to deploy server", e, debug)


@cli.command(help="Open the Arcade Dashboard in a web browser", rich_help_panel="User")
def dashboard(
    host: str = typer.Option(
        PROD_ENGINE_HOST,
        "-h",
        "--host",
        help="The Arcade Engine host that serves the dashboard.",
    ),
    port: Optional[int] = typer.Option(
        None,
        "-p",
        "--port",
        help="The port of the Arcade Engine.",
    ),
    local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="Open the local dashboard instead of the default remote dashboard.",
    ),
    force_tls: bool = typer.Option(
        False,
        "--tls",
        help="Whether to force TLS for the connection to the Arcade Engine.",
    ),
    force_no_tls: bool = typer.Option(
        False,
        "--no-tls",
        help="Whether to disable TLS for the connection to the Arcade Engine.",
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """Opens the Arcade Dashboard in a web browser.

    The Dashboard is a web-based Arcade user interface that is served by the Arcade Engine.
    """
    try:
        if local:
            host = "localhost"

        # Construct base URL (for both health check and dashboard)
        base_url = compute_base_url(force_tls, force_no_tls, host, port)
        dashboard_url = f"{base_url}/dashboard"

        # Try to hit /health endpoint on engine and warn if it is down
        config = validate_and_get_config()
        with Arcade(api_key=config.api.key, base_url=base_url) as client:
            log_engine_health(client)

        # Open the dashboard in a browser
        console.print(f"Opening Arcade Dashboard at {dashboard_url}")
        if not webbrowser.open(dashboard_url):
            console.print(
                f"If a browser doesn't open automatically, copy this URL and paste it into your browser: {dashboard_url}",
                style="dim",
            )
    except Exception as e:
        handle_cli_error("Failed to open dashboard", e, debug)


@cli.callback()
def main_callback(
    ctx: typer.Context,
    _: Optional[bool] = typer.Option(
        None,
        "-v",
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Print version and exit.",
    ),
) -> None:
    # Commands that do not require a logged in user
    public_commands = {
        login.__name__,
        logout.__name__,
        dashboard.__name__,
        evals.__name__,
        mcp.__name__,
        new.__name__,
        show.__name__,
        configure.__name__,
    }
    if ctx.invoked_subcommand in public_commands:
        return

    if not check_existing_login(suppress_message=True):
        handle_cli_error("Not logged in to Arcade CLI. Use `arcade login` to log in.")
