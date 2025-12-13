import functools
import os
import platform
import sys
import time
from importlib import metadata
from typing import Any

import typer
from arcade_cli.usage.constants import (
    EVENT_CLI_COMMAND_EXECUTED,
    EVENT_CLI_COMMAND_FAILED,
    PROP_CLI_VERSION,
    PROP_COMMAND_NAME,
    PROP_ORG_ID,
    PROP_PROJECT_ID,
)
from arcade_core.constants import ARCADE_CONFIG_PATH
from arcade_core.usage import UsageIdentity, UsageService, is_tracking_enabled
from arcade_core.usage.constants import (
    PROP_DEVICE_MONOTONIC_END,
    PROP_DEVICE_MONOTONIC_START,
    PROP_DURATION_MS,
    PROP_ERROR_MESSAGE,
    PROP_OS_RELEASE,
    PROP_OS_TYPE,
    PROP_RUNTIME_LANGUAGE,
    PROP_RUNTIME_VERSION,
)
from rich.console import Console
from typer.core import TyperCommand, TyperGroup
from typer.models import Context

console = Console()


class CommandTracker:
    """Tracks CLI command execution for usage analytics."""

    def __init__(self) -> None:
        self.usage_service = UsageService()
        self.identity = UsageIdentity()
        self._cli_version: str | None = None
        self._runtime_version: str | None = None

    @property
    def cli_version(self) -> str:
        """Get CLI version, cached after first access."""
        if self._cli_version is None:
            try:
                self._cli_version = metadata.version("arcade-mcp")
            except Exception:
                self._cli_version = "unknown"
        return self._cli_version

    @property
    def runtime_language(self) -> str:
        """Get the runtime language (always 'python' for this CLI)."""
        return "python"

    @property
    def runtime_version(self) -> str:
        """Get runtime version, cached after first access."""
        if self._runtime_version is None:
            version_info = sys.version_info
            self._runtime_version = (
                f"{version_info.major}.{version_info.minor}.{version_info.micro}"
            )
        return self._runtime_version

    @property
    def user_id(self) -> str:
        """Get distinct_id based on authentication state."""
        return self.identity.get_distinct_id()

    def get_full_command_path(self, ctx: typer.Context) -> str:
        """Get the full command path by traversing the context hierarchy."""
        command_parts = []
        current_ctx: Any = ctx
        while current_ctx and current_ctx.parent:
            if current_ctx.command.name:
                command_parts.append(current_ctx.command.name)
            current_ctx = current_ctx.parent
        return ".".join(reversed(command_parts))

    def _get_org_project_context(self) -> tuple[str | None, str | None]:
        """Get org_id and project_id from config if available."""
        try:
            from arcade_core.config_model import Config

            config = Config.load_from_file()
            if config.context:
                return config.context.org_id, config.context.project_id
        except FileNotFoundError:
            # No config file - user isn't logged in, which is fine
            pass
        except Exception as e:
            console.print(
                f"[yellow]Warning: Failed to load Arcade config: {e}[/yellow]\n"
                "[yellow]Run 'arcade logout' then 'arcade login' to fix this.[/yellow]"
            )
        return None, None

    def _handle_successful_login(self) -> None:
        """Handle a successful login event.

        Upon a successful login, we retrieve and persist the principal_id for the logged in user.
        We then alias the persisted anon_id to the known person with principal_id.
        As a result, the previous anonymous events will be attributed to the known person with principal_id.
        """
        principal_id = self.identity.get_principal_id()
        if principal_id:
            if self.identity.should_alias():
                # Alias the anon_id to the known person with principal_id
                self.usage_service.alias(
                    previous_id=self.identity.anon_id, distinct_id=principal_id
                )
            # Always update the linked principal_id on successful login
            self.identity.set_linked_principal_id(principal_id)

    def _handle_successful_logout(
        self,
        command_name: str,
        duration_ms: float | None = None,
        monotonic_start: float | None = None,
        monotonic_end: float | None = None,
    ) -> None:
        """Handle a successful logout event.

        Upon a successful logout, we rotate the anon_id and clear the linked principal_id.
        """
        # Check if user was authenticated before logout (has linked_principal_id)
        data = self.identity.load_or_create()
        was_authenticated = data.get("linked_principal_id") is not None

        # Send logout event as the authenticated user before resetting to anonymous
        properties: dict[str, Any] = {
            PROP_COMMAND_NAME: command_name,
            PROP_CLI_VERSION: self.cli_version,
            PROP_RUNTIME_LANGUAGE: self.runtime_language,
            PROP_RUNTIME_VERSION: self.runtime_version,
            PROP_OS_TYPE: platform.system(),
            PROP_OS_RELEASE: platform.release(),
        }
        if duration_ms:
            properties[PROP_DURATION_MS] = round(duration_ms)

        if monotonic_start is not None:
            properties[PROP_DEVICE_MONOTONIC_START] = monotonic_start

        if monotonic_end is not None:
            properties[PROP_DEVICE_MONOTONIC_END] = monotonic_end

        # Check if using anon_id
        is_anon = self.user_id == self.identity.anon_id
        self.usage_service.capture(
            EVENT_CLI_COMMAND_EXECUTED, self.user_id, properties=properties, is_anon=is_anon
        )

        # Only rotate anon_id if user was actually authenticated
        if was_authenticated:
            self.identity.reset_to_anonymous()

    def track_command_execution(
        self,
        command_name: str,
        success: bool,
        duration_ms: float | None = None,
        error_message: str | None = None,
        is_login: bool = False,
        is_logout: bool = False,
        monotonic_start: float | None = None,
        monotonic_end: float | None = None,
    ) -> None:
        """Track command execution event.

        Args:
            command_name: The name of the CLI command that was executed.
            success: Whether the command was successfully executed.
            duration_ms: The duration of the command execution in milliseconds.
            error_message: The error message if the command failed.
            is_login: Whether this is a login command.
            is_logout: Whether this is a logout command.
            monotonic_start: Monotonic clock timestamp at command start.
            monotonic_end: Monotonic clock timestamp at command end.
        """
        if not is_tracking_enabled():
            return

        if is_login and success:
            self._handle_successful_login()

        elif is_logout and success:
            self._handle_successful_logout(
                command_name, duration_ms, monotonic_start, monotonic_end
            )
            return

        # Edge case: Lazy alias check for other commands (if user authenticated via side path)
        elif not is_login and not is_logout and self.identity.should_alias():
            principal_id = self.identity.get_principal_id()
            if principal_id:
                self.usage_service.alias(
                    previous_id=self.identity.anon_id, distinct_id=principal_id
                )
                self.identity.set_linked_principal_id(principal_id)

        event_name = EVENT_CLI_COMMAND_EXECUTED if success else EVENT_CLI_COMMAND_FAILED

        properties: dict[str, Any] = {
            PROP_COMMAND_NAME: command_name,
            PROP_CLI_VERSION: self.cli_version,
            PROP_RUNTIME_LANGUAGE: self.runtime_language,
            PROP_RUNTIME_VERSION: self.runtime_version,
            PROP_OS_TYPE: platform.system(),
            PROP_OS_RELEASE: platform.release(),
        }

        # Add org/project context when available (many commands operate within a project)
        org_id, project_id = self._get_org_project_context()
        if org_id:
            properties[PROP_ORG_ID] = org_id
        if project_id:
            properties[PROP_PROJECT_ID] = project_id

        if not success and error_message:
            properties[PROP_ERROR_MESSAGE] = error_message

        if duration_ms:
            properties[PROP_DURATION_MS] = round(duration_ms)

        if monotonic_start is not None:
            properties[PROP_DEVICE_MONOTONIC_START] = monotonic_start

        if monotonic_end is not None:
            properties[PROP_DEVICE_MONOTONIC_END] = monotonic_end

        # Check if using anon_id (not authenticated)
        is_anon = self.user_id == self.identity.anon_id
        self.usage_service.capture(event_name, self.user_id, properties=properties, is_anon=is_anon)


# Global tracker instance
command_tracker = CommandTracker()


class TrackedTyperCommand(TyperCommand):
    """Custom TyperCommand that tracks individual command execution."""

    def invoke(self, ctx: Any) -> Any:
        """Override invoke to track command execution."""
        if not os.path.exists(ARCADE_CONFIG_PATH):
            console.print(
                "[yellow]Arcade collects CLI usage data to help us debug and improve the service. "
                "By continuing to use the Arcade CLI, you agree to the terms of our Privacy Policy. "
                "To opt out, set the ARCADE_USAGE_TRACKING environment variable to 0.[/yellow]"
            )

        command_name = ctx.command.name
        is_login = command_name == "login"
        is_logout = command_name == "logout"
        try:
            start_time = time.time()
            start_monotonic = time.monotonic()
            result = super().invoke(ctx)
            end_time = time.time()
            end_monotonic = time.monotonic()
            duration = end_time - start_time
            command_tracker.track_command_execution(
                command_tracker.get_full_command_path(ctx),
                success=True,
                duration_ms=duration * 1000,
                is_login=is_login,
                is_logout=is_logout,
                monotonic_start=start_monotonic,
                monotonic_end=end_monotonic,
            )
        except Exception as e:
            end_time = time.time()
            end_monotonic = time.monotonic()
            duration = end_time - start_time

            from arcade_cli.utils import CLIError

            error_msg = str(e)[:300]
            command_tracker.track_command_execution(
                command_tracker.get_full_command_path(ctx),
                success=False,
                duration_ms=duration * 1000,
                error_message=error_msg,
                is_login=is_login,
                is_logout=is_logout,
                monotonic_start=start_monotonic,
                monotonic_end=end_monotonic,
            )

            if isinstance(e, CLIError):
                raise typer.Exit(code=1)
            else:
                raise
        else:
            return result


class TrackedTyperGroup(TyperGroup):
    """Custom TyperGroup that creates tracked commands."""

    def command(self, *args: Any, **kwargs: Any) -> Any:
        """Override command decorator to use TrackedTyperCommand."""
        # Set the custom command class
        kwargs["cls"] = TrackedTyperCommand
        result: Any = super().command(*args, **kwargs)
        return result

    def list_commands(self, ctx: Context) -> list[str]:  # type: ignore[override]
        """Return list of commands in the order appear."""
        return list(self.commands)


class TrackedTyper(typer.Typer):
    """Custom Typer that creates tracked commands."""

    def command(
        self, name: str | None = None, *, cls: type[TyperCommand] | None = None, **kwargs: Any
    ) -> Any:
        """Override command decorator to use TrackedTyperCommand."""
        if cls is None:
            cls = TrackedTyperCommand

        result: Any = super().command(name, cls=cls, **kwargs)
        return result

    def callback(self, name: str | None = None, **kwargs: Any) -> Any:
        """Override callback decorator to track callback execution."""
        original_callback_decorator: Any = super().callback(name, **kwargs)

        def decorator(func: Any) -> Any:
            @functools.wraps(func)
            def tracked_callback(*args: Any, **cb_kwargs: Any) -> Any:
                """Wrapper that tracks callback execution."""
                # Get the context from kwargs (Typer passes it)
                ctx = cb_kwargs.get("ctx") or (
                    args[0] if args and isinstance(args[0], typer.Context) else None
                )

                command_name = ctx.invoked_subcommand if ctx and ctx.invoked_subcommand else "root"
                start_time = time.time()
                start_monotonic = time.monotonic()

                try:
                    result = func(*args, **cb_kwargs)
                except Exception as e:
                    # Track callback failure (auth failures, version checks, etc.)
                    end_time = time.time()
                    end_monotonic = time.monotonic()
                    duration = (end_time - start_time) * 1000

                    from arcade_cli.utils import CLIError

                    command_tracker.track_command_execution(
                        command_name,
                        success=False,
                        duration_ms=duration,
                        error_message=str(e)[:300],
                        monotonic_start=start_monotonic,
                        monotonic_end=end_monotonic,
                    )

                    if isinstance(e, CLIError):
                        raise typer.Exit(code=1)
                    else:
                        raise
                else:
                    return result

            result: Any = original_callback_decorator(tracked_callback)
            return result

        return decorator
