import importlib.util
import ipaddress
import os
import shlex
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from importlib import metadata
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, cast
from urllib.parse import urlparse

import idna
from arcade_core import ToolCatalog, Toolkit
from arcade_core.config_model import Config
from arcade_core.constants import LOCALHOST
from arcade_core.discovery import (
    analyze_files_for_tools,
    build_minimal_toolkit,
    collect_tools_from_modules,
    find_candidate_tool_files,
)
from arcade_core.errors import ToolkitLoadError
from arcade_core.network.org_transport import build_org_scoped_http_client
from arcade_core.schema import ToolDefinition
from arcadepy import (
    NOT_GIVEN,
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    Arcade,
)
from arcadepy.types import AuthorizationResponse
from pydantic import ValidationError
from rich.console import Console
from rich.markup import escape
from typer.core import TyperGroup
from typer.models import Context

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


class Provider(str, Enum):
    """Supported model providers for evaluations."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"


# ============================================================================
# Default Models Configuration
# ============================================================================
# Edit these values to change the default models used by the CLI.
# These are used when --models is not specified.
#
# Note: Anthropic models include date suffixes (e.g., -20250929) which may need
# periodic updates. Check https://docs.anthropic.com/en/docs/about-claude/models
# for the latest model identifiers.

DEFAULT_MODELS: dict[Provider, str] = {
    Provider.OPENAI: "gpt-4o",
    Provider.ANTHROPIC: "claude-sonnet-4-5-20250929",
}


def get_default_model(provider: Provider) -> str:
    """Get the default model for a provider.

    Args:
        provider: The provider to get the default model for.

    Returns:
        The default model name for the provider.
    """
    return DEFAULT_MODELS.get(provider, "gpt-4o")


# ============================================================================
# Output Format Detection
# ============================================================================

ALL_OUTPUT_FORMATS = ["txt", "md", "html", "json"]


def parse_output_paths(output_paths: list[str] | None) -> tuple[str | None, list[str]]:
    """Parse --output/-o paths into base path and format list.

    Supports:
    - Single file with extension: "results.json" → ("results", ["json"])
    - Multiple files: ["results.md", "results.html"] → ("results", ["md", "html"])
    - No extension: "results" → ("results", ["txt", "md", "html", "json"])

    Args:
        output_paths: List of output paths from --output/-o flag.

    Returns:
        Tuple of (base_path, formats). Returns (None, []) if no paths.

    Raises:
        ValueError: If paths have inconsistent base names or invalid extensions.
    """
    if not output_paths:
        return None, []

    # Extract base path and formats
    base_path = None
    formats: list[str] = []

    for path_str in output_paths:
        path = Path(path_str)
        stem = path.stem
        ext = path.suffix.lstrip(".")

        # Determine base path (all paths should have same base)
        if base_path is None:
            base_path = str(Path(path.parent) / stem)
        elif str(Path(path.parent) / stem) != base_path:
            raise ValueError(
                f"Output paths have different base names: '{base_path}' vs '{Path(path.parent) / stem}'. "
                "All outputs must use the same base path."
            )

        # No extension means all formats
        if not ext:
            formats = ALL_OUTPUT_FORMATS.copy()
            break

        # Validate extension
        if ext not in ALL_OUTPUT_FORMATS:
            valid = ", ".join(ALL_OUTPUT_FORMATS)
            raise ValueError(f"Invalid output format '.{ext}'. Valid extensions: {valid}")

        if ext not in formats:
            formats.append(ext)

    return base_path, formats


def parse_api_key_spec(spec: str) -> tuple[Provider, str]:
    """Parse --api-key value into (provider, key).

    Args:
        spec: API key spec string. Format: "provider:key"
              Examples: "openai:sk-...", "anthropic:sk-ant-..."

    Returns:
        Tuple of (Provider, api_key_string).

    Raises:
        ValueError: If format is invalid or provider is unknown.
    """
    if ":" not in spec:
        raise ValueError(
            f"Invalid --api-key format: '{spec}'. "
            "Expected format: 'provider:key' (e.g., 'openai:sk-...')"
        )

    provider_str, key = spec.split(":", 1)
    provider_str = provider_str.strip().lower()
    key = key.strip()

    if not key:
        raise ValueError(f"Empty API key for provider '{provider_str}'")

    try:
        provider = Provider(provider_str)
    except ValueError:
        valid_providers = [p.value for p in Provider]
        raise ValueError(
            f"Invalid provider '{provider_str}' in --api-key. "
            f"Valid providers: {', '.join(valid_providers)}"
        )

    return provider, key


# ============================================================================
# Multi-Provider Model Specification
# ============================================================================


@dataclass
class ProviderConfig:
    """Configuration for a single provider from CLI input.

    Parsed from --use-provider flag values like:
    - "openai" -> provider=OPENAI, models=[] (use default)
    - "openai:gpt-4o,gpt-4o-mini" -> provider=OPENAI, models=["gpt-4o", "gpt-4o-mini"]
    """

    provider: Provider
    models: list[str]  # Empty list means use default model

    def get_models(self) -> list[str]:
        """Get models, using default if none specified."""
        if self.models:
            return self.models
        return [get_default_model(self.provider)]


@dataclass
class ModelSpec:
    """A specific model to run evaluations against.

    This is the expanded form used by the runner - one ModelSpec per
    (provider, model, api_key) combination.
    """

    provider: Provider
    model: str
    api_key: str

    @property
    def display_name(self) -> str:
        """Get display name in format 'provider/model'."""
        return f"{self.provider.value}/{self.model}"


def parse_provider_spec(spec: str) -> ProviderConfig:
    """Parse a --use-provider value into a ProviderConfig.

    Args:
        spec: Provider spec string. Examples:
            - "openai" -> use OpenAI with default model
            - "openai:gpt-4o" -> use OpenAI with gpt-4o
            - "anthropic:claude-sonnet-4-5-20250929,claude-3-haiku-20240307"

    Returns:
        ProviderConfig with parsed provider and models.

    Raises:
        ValueError: If provider name is invalid.

    Examples:
        >>> parse_provider_spec("openai")
        ProviderConfig(provider=Provider.OPENAI, models=[])
        >>> parse_provider_spec("openai:gpt-4o,gpt-4o-mini")
        ProviderConfig(provider=Provider.OPENAI, models=['gpt-4o', 'gpt-4o-mini'])
    """
    if ":" in spec:
        provider_str, models_str = spec.split(":", 1)
        models = [m.strip() for m in models_str.split(",") if m.strip()]
    else:
        provider_str = spec.strip()
        models = []

    # Validate provider
    provider_str_lower = provider_str.lower()
    try:
        provider = Provider(provider_str_lower)
    except ValueError:
        valid_providers = [p.value for p in Provider]
        raise ValueError(
            f"Invalid provider '{provider_str}'. Valid providers: {', '.join(valid_providers)}"
        )

    return ProviderConfig(provider=provider, models=models)


def expand_provider_configs(
    configs: list[ProviderConfig],
    api_keys: dict[Provider, str | None],
) -> list[ModelSpec]:
    """Expand provider configs into individual ModelSpecs with resolved API keys.

    Args:
        configs: List of ProviderConfig from parsed --use-provider flags.
        api_keys: Dict mapping Provider to API key (from flags or env vars).

    Returns:
        List of ModelSpec, one per (provider, model) combination.

    Raises:
        ValueError: If API key is missing for any provider.
    """
    model_specs: list[ModelSpec] = []

    for config in configs:
        api_key = api_keys.get(config.provider)
        if not api_key:
            env_var = f"{config.provider.value.upper()}_API_KEY"
            raise ValueError(
                f"API key required for provider '{config.provider.value}'. "
                f"Provide via --{config.provider.value}-key or set {env_var} environment variable."
            )

        for model in config.get_models():
            model_specs.append(ModelSpec(provider=config.provider, model=model, api_key=api_key))

    return model_specs


def resolve_provider_api_keys(
    api_keys_specs: list[str] | None = None,
) -> dict[Provider, str | None]:
    """Resolve API keys for all providers from flags and environment.

    Priority: --api-key flag > environment variable > .env file

    Args:
        api_keys_specs: List of provider:key specs from --api-key flags.

    Returns:
        Dict mapping Provider to resolved API key (or None if not found).
    """
    from dotenv import dotenv_values

    # Load .env file
    env_values = dotenv_values(".env")

    # Start with empty dict
    keys: dict[Provider, str | None] = {
        Provider.OPENAI: None,
        Provider.ANTHROPIC: None,
    }

    # Parse --api-key provider:key specs (highest priority)
    if api_keys_specs:
        for spec in api_keys_specs:
            try:
                provider, key = parse_api_key_spec(spec)
                keys[provider] = key
            except ValueError as e:
                # Re-raise to let CLI handle error
                raise ValueError(str(e)) from e

    # Fallback to environment variables and .env file
    def resolve_key_from_env(env_var: str) -> str | None:
        # Check current environment
        key = os.environ.get(env_var)
        if key:
            return key
        # Check .env file
        return env_values.get(env_var)

    # Set from environment if not already set by --api-key
    if keys[Provider.OPENAI] is None:
        keys[Provider.OPENAI] = resolve_key_from_env("OPENAI_API_KEY")
    if keys[Provider.ANTHROPIC] is None:
        keys[Provider.ANTHROPIC] = resolve_key_from_env("ANTHROPIC_API_KEY")

    return keys


class CLIError(Exception):
    """Custom exception for CLI errors that preserves error messages for tracking.

    Never use this exception directly. Use handle_cli_error utility function instead.
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        self.message = message
        self.original_error = original_error
        super().__init__(message)

    def __str__(self) -> str:
        if self.original_error:
            return f"{self.message}: {self.original_error!s}"
        return self.message


def handle_cli_error(
    message: str,
    error: Exception | None = None,
    debug: bool = True,
    should_exit: bool = True,
) -> None:
    """Handle CLI error reporting with optional debug traceback and exit."""
    if error and debug:
        console.print(f"❌ {message}: {traceback.format_exc()}", style="bold red")
    elif error:
        console.print(f"❌ {message}: {escape(str(error))}", style="bold red")
    else:
        console.print(f"❌ {escape(message)}", style="bold red")

    if should_exit:
        raise CLIError(message, error)


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
                handle_cli_error(f"{e}")
    else:
        toolkits = Toolkit.find_all_arcade_toolkits()

    if not toolkits:
        handle_cli_error("No toolkits found or specified")

    catalog = ToolCatalog()
    for loaded_toolkit in toolkits:
        if show_toolkits:
            console.print(f"Loading toolkit: {loaded_toolkit.name}", style="bold blue")
        catalog.add_toolkit(loaded_toolkit)
    return catalog


def _discover_installed_toolkits(catalog: ToolCatalog) -> ToolCatalog:
    for tk in Toolkit.find_all_arcade_toolkits():
        catalog.add_toolkit(tk)
    return catalog


def create_cli_catalog_local() -> ToolCatalog:
    """
    Load a local toolkit from the current working directory if a pyproject.toml is present.
    Fallback to environment discovery if not present.
    """
    cwd = Path.cwd()
    catalog = ToolCatalog()

    if not (cwd / "pyproject.toml").is_file():
        return _discover_installed_toolkits(catalog)

    try:
        files = find_candidate_tool_files(cwd)
        if not files:
            return _discover_installed_toolkits(catalog)

        files_with_tools = analyze_files_for_tools(files)
        if not files_with_tools:
            return _discover_installed_toolkits(catalog)

        discovered_tools = collect_tools_from_modules(files_with_tools)
        if not discovered_tools:
            return _discover_installed_toolkits(catalog)

        toolkit = build_minimal_toolkit(
            server_name=cwd.name,
            server_version="0.1.0dev",
            description=f"Local toolkit from {cwd.name}",
        )
        # Add tools directly to catalog using the discovery approach
        for tool_func, module in discovered_tools:
            # Register module in sys.modules so it can be found
            if module.__name__ not in sys.modules:
                sys.modules[module.__name__] = module
            catalog.add_tool(tool_func, toolkit, module)
    except Exception as e:
        console.log(
            f"Local file discovery failed: {e}; falling back to installed toolkits",
            style="dim",
        )
    else:
        return catalog

    # Fallback: discover installed toolkits
    return _discover_installed_toolkits(catalog)


def compute_base_url(
    force_tls: bool,
    force_no_tls: bool,
    host: str,
    port: int | None,
    default_port: int | None = 9099,
) -> str:
    """
    Compute the base URL for an Arcade service from the provided overrides.

    Treats 127.0.0.1 and 0.0.0.0 as aliases for localhost.

    force_no_tls takes precedence over force_tls. For example, if both are set to True,
    the resulting URL will use http.

    The port is included in the URL unless the host is a fully qualified domain name
    (excluding IP addresses) and no port is specified. Handles IPv4, IPv6, IDNs, and
    hostnames with underscores.

    This property exists to provide a consistent and correctly formatted URL for
    connecting to Arcade services (Engine, Coordinator), taking into account various
    configuration options and edge cases. It ensures that:

    1. The correct protocol (http/https) is used based on the TLS setting.
    2. IPv4 and IPv6 addresses are properly formatted.
    3. Internationalized Domain Names (IDNs) are correctly encoded.
    4. Fully Qualified Domain Names (FQDNs) are identified and handled appropriately.
    5. Ports are included when necessary, respecting common conventions for FQDNs.
    6. Hostnames with underscores (common in development environments) are supported.
    7. Pre-existing port specifications in the host are respected.

    Args:
        force_tls: Force HTTPS protocol.
        force_no_tls: Force HTTP protocol (takes precedence over force_tls).
        host: The hostname or IP address.
        port: The port number (optional).
        default_port: The default port for localhost if none specified.
            Use 9099 for Engine, None for Coordinator (standard HTTPS).

    Returns:
        str: The fully constructed URL for the Arcade service.
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

    # "localhost" defaults to dev port if not specified and a default is provided
    if host == LOCALHOST and port is None and default_port is not None:
        port = default_port

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


def get_tools_from_engine(
    host: str,
    port: int | None = None,
    force_tls: bool = False,
    force_no_tls: bool = False,
    toolkit: str | None = None,
) -> list[ToolDefinition]:
    base_url = compute_base_url(force_tls, force_no_tls, host, port)
    client = get_arcade_client(base_url)

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
            f"❌ Can't connect to Arcade Engine at {base_url}. (Is it running?)",
            style="bold red",
        )

    return tools


def validate_and_get_config(
    validate_api: bool = True,
    validate_user: bool = True,
) -> Config:
    """
    Validates the configuration, user, and returns the Config object.
    """
    try:
        from arcade_core.config import config
    except Exception as e:
        handle_cli_error("Not logged in", e, debug=False)

    if validate_api and not config.auth:
        handle_cli_error("Authentication not configured. Please run `arcade login`.")

    if validate_user and (not config.user or not config.user.email):
        handle_cli_error("User email not found in configuration. Please run `arcade login`.")

    return config


def get_org_project_context() -> tuple[str, str]:
    """
    Get the active org_id and project_id from config.

    Returns:
        Tuple of (org_id, project_id)

    Raises:
        CLIError if no active org/project context is set.
    """
    config = validate_and_get_config()

    if not config.context or not config.context.org_id or not config.context.project_id:
        handle_cli_error("No active organization/project set. Please run `arcade login` first.")
        raise AssertionError("unreachable")  # handle_cli_error raises CLIError

    return config.context.org_id, config.context.project_id


def get_auth_headers(coordinator_url: str | None = None) -> dict[str, str]:
    """
    Get authorization headers for API calls.

    Args:
        coordinator_url: Coordinator URL for token refresh (optional for legacy)

    Returns:
        Dictionary with Authorization header
    """
    from arcade_core.constants import PROD_COORDINATOR_HOST

    from arcade_cli.authn import get_valid_access_token

    config = validate_and_get_config()
    resolved_coordinator_url = (
        coordinator_url
        or (getattr(config, "coordinator_url", None) or None)
        or f"https://{PROD_COORDINATOR_HOST}"
    )

    try:
        access_token = get_valid_access_token(resolved_coordinator_url)
    except ValueError as e:
        handle_cli_error(str(e))
        raise AssertionError("unreachable")  # handle_cli_error raises CLIError

    return {"Authorization": f"Bearer {access_token}"}


def get_org_scoped_url(base_url: str, path: str) -> str:
    """
    Build an org-scoped URL using the active context.

    Args:
        base_url: Base URL of the API (e.g., https://api.arcade.dev)
        path: Path suffix after the org/project prefix (e.g., "/secrets/KEY")

    Returns:
        Full URL with org/project path prefix

    Raises:
        CLIError if no active context is set

    Example:
        get_org_scoped_url("https://api.arcade.dev", "/secrets/MY_KEY")
        # Returns: "https://api.arcade.dev/v1/orgs/ORG_ID/projects/PROJECT_ID/secrets/MY_KEY"
    """
    config = validate_and_get_config()

    if not config.context:
        handle_cli_error("No active organization/project. Please run `arcade login` first.")
        raise AssertionError("unreachable")  # handle_cli_error raises CLIError

    org_id = config.context.org_id
    project_id = config.context.project_id

    return f"{base_url}/v1/orgs/{org_id}/projects/{project_id}{path}"


def get_arcade_client(base_url: str) -> Arcade:
    """
    Create an Arcade client with proper authentication and org-scoped URL rewriting.
    Requests are automatically rewritten to include org/project scope in URLs.

    Args:
        base_url: Base URL of the Arcade Engine

    Returns:
        Configured Arcade client

    Example:
        client = get_arcade_client("https://api.arcade.dev")
        servers = client.workers.list()  # Automatically uses org-scoped URLs
    """
    config = validate_and_get_config()

    # OAuth mode: need to rewrite URLs to include org/project scope
    from arcade_cli.authn import get_valid_access_token

    access_token = get_valid_access_token()

    # Get org/project context for URL rewriting
    if not config.context or not config.context.org_id or not config.context.project_id:
        handle_cli_error("No active organization/project set. Please run `arcade login` first.")
        raise AssertionError("unreachable")  # handle_cli_error raises CLIError

    org_id = config.context.org_id
    project_id = config.context.project_id

    http_client = build_org_scoped_http_client(org_id, project_id)

    return Arcade(api_key=access_token, base_url=base_url, http_client=http_client)


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
        # Directories to exclude from recursive search
        exclude_dirs = {
            ".venv",
            "venv",
            ".env",
            "env",
            "node_modules",
            "__pycache__",
            ".git",
            "build",
            "dist",
            ".tox",
            "htmlcov",
            "site-packages",
            ".pytest_cache",
        }

        eval_files = []
        for f in directory_path.rglob("eval_*.py"):
            if f.is_file():
                # Check if any parent directory is in exclude_dirs
                should_exclude = any(part in exclude_dirs for part in f.parts)
                if not should_exclude:
                    eval_files.append(f)
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

        # Add the directory containing the eval file to sys.path temporarily
        # so that the eval file can import other modules in the same directory
        eval_dir = str(eval_file_path.parent)
        original_path = sys.path.copy()
        if eval_dir not in sys.path:
            sys.path.insert(0, eval_dir)

        try:
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
                console.print(
                    f"No @tool_eval functions found in {eval_file_path}",
                    style="bold yellow",
                )
                continue

            eval_suites.extend(eval_suite_funcs)
        except Exception as e:
            console.print(f"Failed to load {eval_file_path}: {e}", style="bold red")
            continue
        finally:
            # Restore the original sys.path
            sys.path[:] = original_path

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
    port: int | None,
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
            worker=False,
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
        version = metadata.version("arcade-mcp")
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


def resolve_provider_api_key(provider: Provider, provider_api_key: str | None = None) -> str | None:
    """
    Resolve the API key for a given provider for evals.

    Args:
        provider: The model provider
        provider_api_key: API key provided via CLI argument

    Returns:
        The resolved API key or None if not found
    """
    if provider_api_key:
        return provider_api_key

    # Map providers to their environment variable names
    provider_env_vars = {
        Provider.OPENAI: "OPENAI_API_KEY",
        Provider.ANTHROPIC: "ANTHROPIC_API_KEY",
    }

    env_var_name = provider_env_vars.get(provider)
    if not env_var_name:
        return None

    # First check current environment
    api_key = os.getenv(env_var_name)
    if api_key:
        return api_key

    # Then check .env file in current working directory
    env_file_path = Path.cwd() / ".env"
    if env_file_path.exists():
        load_dotenv(env_file_path, override=False)
        api_key = os.getenv(env_var_name)
        if api_key:
            return api_key

    return None


def filter_failed_evaluations(
    all_evaluations: list[list[dict[str, Any]]],
) -> tuple[list[list[dict[str, Any]]], tuple[int, int, int, int]]:
    """
    Filter evaluation results to show only failed cases and calculate original counts.

    Args:
        all_evaluations: List of evaluation results with structure:
            [[{model: str, rubric: str, cases: [{name, input, evaluation}]}]]

    Returns:
        Tuple of (filtered_evaluations, original_counts) where original_counts is
        (total_cases, total_passed, total_failed, total_warned)
    """
    original_total_cases = 0
    original_total_passed = 0
    original_total_failed = 0
    original_total_warned = 0

    # Calculate original counts before filtering
    for eval_suite in all_evaluations:
        for model_results in eval_suite:
            for case in model_results.get("cases", []):
                evaluation = case["evaluation"]
                original_total_cases += 1
                if evaluation.passed:
                    original_total_passed += 1
                elif evaluation.warning:
                    original_total_warned += 1
                else:
                    original_total_failed += 1

    # Filter to show only failed evaluations
    filtered_evaluations = []
    for eval_suite in all_evaluations:
        filtered_suite = []
        for model_results in eval_suite:
            filtered_cases = [
                case
                for case in model_results.get("cases", [])
                if not case["evaluation"].passed and not case["evaluation"].warning
            ]
            if filtered_cases:  # Only include model results with failed cases
                filtered_model_results = model_results.copy()
                filtered_model_results["cases"] = filtered_cases
                filtered_suite.append(filtered_model_results)
        if filtered_suite:
            filtered_evaluations.append(filtered_suite)

    original_counts = (
        original_total_cases,
        original_total_passed,
        original_total_failed,
        original_total_warned,
    )

    return filtered_evaluations, original_counts


def require_dependency(
    package_name: str,
    command_name: str,
    uv_install_command: str,
    pip_install_command: str,
) -> None:
    """
    Display a helpful error message if the required dependency is missing.

    Args:
        package_name: The name of the package to import (e.g., 'arcade_serve')
        command_name: The command that requires the package (e.g., 'evals')
        uv_install_command: The uv command to install the package (e.g., "uv tool install 'arcade-mcp[evals]'")
        pip_install_command: The pip command to install the package (e.g., "pip install 'arcade-mcp[evals]'")
    """
    try:
        importlib.import_module(package_name.replace("-", "_"))
    except ImportError:
        error_message = (
            f"The '{package_name}' package is required to run the '{command_name}' command but is not installed.\n\n"
            f"To install it:\n"
            f"  - If using uv: {uv_install_command}\n"
            f"  - If using pip: {pip_install_command}"
        )
        handle_cli_error(error_message)
