import asyncio
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import click
import typer
from arcade_core.constants import CREDENTIALS_FILE_PATH, PROD_COORDINATOR_HOST, PROD_ENGINE_HOST
from arcadepy import Arcade
from rich.console import Console

from arcade_cli.authn import (
    OAuthLoginError,
    _credentials_file_contains_legacy,
    build_coordinator_url,
    check_existing_login,
    perform_oauth_login,
    save_credentials_from_whoami,
)
from arcade_cli.evals_runner import run_capture, run_evaluations
from arcade_cli.org import app as org_app
from arcade_cli.project import app as project_app
from arcade_cli.secret import app as secret_app
from arcade_cli.server import app as server_app
from arcade_cli.show import show_logic
from arcade_cli.usage.command_tracker import TrackedTyper, TrackedTyperGroup
from arcade_cli.utils import (
    ModelSpec,
    Provider,
    compute_base_url,
    expand_provider_configs,
    get_default_model,
    get_eval_files,
    handle_cli_error,
    load_eval_suites,
    log_engine_health,
    parse_output_paths,
    parse_provider_spec,
    require_dependency,
    resolve_provider_api_keys,
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


@cli.command(help="Log in to Arcade", rich_help_panel="User")
def login(
    host: str = typer.Option(
        PROD_COORDINATOR_HOST,
        "-h",
        "--host",
        help="The Arcade Coordinator host to log in to.",
    ),
    port: Optional[int] = typer.Option(
        None,
        "-p",
        "--port",
        help="The port of the Arcade Coordinator host (if running locally).",
    ),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Logs the user into Arcade using OAuth.
    """
    if check_existing_login():
        console.print("\nTo log out and delete your locally-stored credentials, use ", end="")
        console.print("arcade logout", style="bold green", end="")
        console.print(".\n")
        return

    coordinator_url = build_coordinator_url(host, port)

    try:
        result = perform_oauth_login(
            coordinator_url,
            on_status=lambda msg: console.print(msg, style="dim"),
        )

        # Save credentials
        save_credentials_from_whoami(result.tokens, result.whoami, coordinator_url)

        # Success message
        console.print(f"\n✅ Logged in as {result.email}.", style="bold green")
        if result.selected_org and result.selected_project:
            console.print(
                f"\nActive project: {result.selected_org.name} / {result.selected_project.name}",
                style="dim",
            )
        console.print(
            "Run 'arcade org list' or 'arcade project list' to see available options.",
            style="dim",
        )

    except OAuthLoginError as e:
        if debug:
            console.print(f"Debug: {e.__cause__}", style="dim")
        handle_cli_error(str(e), should_exit=False)
    except KeyboardInterrupt:
        console.print("\nLogin cancelled.", style="yellow")
    except Exception as e:
        handle_cli_error("Login failed", e, debug)


@cli.command(help="Log out of Arcade", rich_help_panel="User")
def logout(
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Logs the user out of Arcade.
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


@cli.command(help="Show current login status and active context", rich_help_panel="User")
def whoami(
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug information"),
) -> None:
    """
    Display the current logged-in user and active organization/project.
    """
    from arcade_core.config_model import Config

    try:
        config = Config.load_from_file()
    except Exception as e:
        handle_cli_error("Failed to read credentials", e, debug)
        return

    # Defensive - should not happen, because the main() callback prevents this:
    if not config.auth:
        console.print("Not logged in. Run 'arcade login' to authenticate.", style="bold red")
        return

    email = config.user.email if config.user else "unknown"
    console.print(f"Logged in as: {email}", style="bold green")

    if config.context:
        console.print(f"\nActive organization: {config.context.org_name}", style="bold")
        console.print(f"   ID: {config.context.org_id}", style="dim")
        console.print(f"\nActive project: {config.context.project_name}", style="bold")
        console.print(f"   ID: {config.context.project_id}", style="dim")
    else:
        console.print("\nNo active organization/project set.", style="yellow")

    console.print("\nRun 'arcade org list' or 'arcade project list' to see options.", style="dim")


cli.add_typer(
    org_app,
    name="org",
    help="Manage organizations (list, set active)",
    rich_help_panel="User",
)

cli.add_typer(
    project_app,
    name="project",
    help="Manage projects (list, set active)",
    rich_help_panel="User",
)


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
    use_provider: Optional[str] = typer.Option(
        None,
        "--use-provider",
        "-p",
        help="Provider(s) and models to use. Format: 'provider' or 'provider:model1,model2'. "
        "Multiple providers: separate with spaces. "
        "Examples: 'openai' or 'openai:gpt-4o anthropic:claude-sonnet-4-5-20250929'",
    ),
    api_key: Optional[list[str]] = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key(s) for provider(s). Format: 'provider:key'. "
        "Can be repeated. Examples: --api-key openai:sk-... --api-key anthropic:sk-ant-...",
    ),
    only_failed: bool = typer.Option(
        False,
        "--only-failed",
        "-f",
        help="Show only failed evaluations",
    ),
    output: Optional[list[str]] = typer.Option(
        None,
        "--output",
        "-o",
        help="Output file(s) with auto-detected format from extension. "
        "Examples: -o results.json, -o results.md -o results.html, -o results (all formats). "
        "Can be repeated for multiple formats.",
    ),
    capture: bool = typer.Option(
        False,
        "--capture",
        help="Run in capture mode - record tool calls without evaluation scoring",
    ),
    include_context: bool = typer.Option(
        False,
        "--include-context",
        help="Include system_message and additional_messages in output (works for both eval and capture modes)",
    ),
    host: Optional[str] = typer.Option(
        None,
        "--host",
        help="Arcade API host for gateway connections (e.g., 'api.bosslevel.dev')",
    ),
    port: Optional[int] = typer.Option(
        None,
        "--port",
        help="Arcade API port for gateway connections (default: 443 for HTTPS)",
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
        uv_install_command=r"uv tool install 'arcade-mcp[evals]'",
        pip_install_command=r"pip install 'arcade-mcp[evals]'",
    )
    # Although Evals does not depend on the TDK, some evaluations import the
    # ToolCatalog class from the TDK instead of from arcade_core, so we require
    # the TDK to run the evals CLI command to avoid possible import errors.
    require_dependency(
        package_name="arcade_tdk",
        command_name="evals",
        uv_install_command=r"uv pip install arcade-tdk",
        pip_install_command=r"pip install arcade-tdk",
    )

    # --- Build model specs from flags ---
    model_specs: list[ModelSpec] = []

    # Resolve API keys from --api-key flags and environment
    api_keys = resolve_provider_api_keys(api_keys_specs=api_key)

    if use_provider:
        # Parse provider specs - supports space-separated values
        # e.g., "openai:gpt-4o anthropic:claude"
        provider_specs = use_provider.split()
        try:
            provider_configs = [parse_provider_spec(spec) for spec in provider_specs]
        except ValueError as e:
            handle_cli_error(str(e), should_exit=True)
            return  # For type checker

        # Expand to model specs
        try:
            model_specs = expand_provider_configs(provider_configs, api_keys)
        except ValueError as e:
            handle_cli_error(str(e), should_exit=True)
            return  # For type checker
    else:
        # Default: OpenAI with default model
        if not api_keys.get(Provider.OPENAI):
            handle_cli_error(
                "API key not found for provider 'openai'. "
                "Please provide it via --api-key openai:KEY, set the OPENAI_API_KEY environment variable, "
                "or add it to a .env file in the current directory.\n\n"
                "Tip: Use --use-provider to specify a different provider (e.g., --use-provider anthropic)",
                should_exit=True,
            )
            return  # For type checker

        model_specs = [
            ModelSpec(
                provider=Provider.OPENAI,
                model=get_default_model(Provider.OPENAI),
                api_key=api_keys[Provider.OPENAI],  # type: ignore[arg-type]
            )
        ]

    if not model_specs:
        handle_cli_error("No models specified. Use --use-provider to specify models.")
        return

    eval_files = get_eval_files(directory)
    if not eval_files:
        return

    # Warn about incompatible flag combinations
    if capture:
        console.print("\nRunning in capture mode", style="bold cyan")
        if only_failed:
            console.print("[yellow]⚠️  --only-failed is ignored in capture mode[/yellow]")
        if show_details:
            console.print("[yellow]⚠️  --details is ignored in capture mode[/yellow]")
    else:
        console.print("\nRunning evaluations", style="bold")

    # Show which models will be used
    unique_providers = {spec.provider.value for spec in model_specs}
    if len(unique_providers) > 1:
        console.print(
            f"[bold cyan]Using {len(model_specs)} model(s) across {len(unique_providers)} providers[/bold cyan]"
        )
    for spec in model_specs:
        console.print(f"  • {spec.display_name}", style="dim")

    # Set arcade URL override BEFORE loading suites (so MCP connections use it)
    if host or port:
        # Build URL from --host and --port
        if not host:
            handle_cli_error("--port requires --host to be specified", should_exit=True)
            return

        # Default to HTTPS on port 443
        scheme = "https"
        port_str = f":{port}" if port and port != 443 else ""
        constructed_url = f"{scheme}://{host}{port_str}"
        os.environ["ARCADE_API_BASE_URL"] = constructed_url

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

    # Parse output paths with smart format detection
    final_output_file: str | None = None
    final_output_formats: list[str] = []

    if output:
        try:
            final_output_file, final_output_formats = parse_output_paths(output)
        except ValueError as e:
            handle_cli_error(str(e), should_exit=True)
            return

    try:
        if capture:
            asyncio.run(
                run_capture(
                    eval_suites=eval_suites,
                    model_specs=model_specs,
                    max_concurrent=max_concurrent,
                    include_context=include_context,
                    output_file=final_output_file,
                    output_format=",".join(final_output_formats) if final_output_formats else "txt",
                    console=console,
                )
            )
        else:
            asyncio.run(
                run_evaluations(
                    eval_suites=eval_suites,
                    model_specs=model_specs,
                    max_concurrent=max_concurrent,
                    show_details=show_details,
                    output_file=final_output_file,
                    output_format=",".join(final_output_formats) if final_output_formats else "txt",
                    failed_only=only_failed,
                    include_context=include_context,
                    console=console,
                )
            )
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
        with Arcade(api_key="", base_url=base_url) as client:
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

    if _credentials_file_contains_legacy():
        console.print(
            "\nYour credentials are from an older CLI version and are no longer supported.",
            style="bold yellow",
        )
        console.print(
            "Run `arcade logout` to remove the old credentials, "
            "then run `arcade login` to sign back in.",
            style="bold yellow",
        )
        console.print(
            "\nNote: `arcade logout` will delete your API key from ~/.arcade/credentials.yaml. "
            "If you need to preserve it, copy it before logging out.",
            style="bold yellow",
        )
        handle_cli_error("Legacy credentials detected. Please re-authenticate.")

    if not check_existing_login(suppress_message=True):
        handle_cli_error("Not logged in to Arcade CLI. Use `arcade login` to log in.")
