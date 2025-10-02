import functools
import platform
import sys
import time
from importlib import metadata
from typing import Any, Callable

import typer
from arcade_cli.usage.identity import UsageIdentity
from arcade_cli.usage.usage_service import UsageService
from arcade_cli.usage.utils import is_tracking_enabled
from typer.core import TyperCommand, TyperGroup
from typer.models import Context


class CommandTracker:
    """Tracks CLI command execution for usage analytics."""

    def __init__(self) -> None:
        self.usage_service = UsageService()
        self.identity = UsageIdentity()
        self._cli_version = None
        self._python_version = None

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
    def python_version(self) -> str:
        """Get Python version, cached after first access."""
        if self._python_version is None:
            version_info = sys.version_info
            self._python_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        return self._python_version

    @property
    def user_id(self) -> str:
        """Get distinct_id based on authentication state."""
        return self.identity.get_distinct_id()

    def get_full_command_path(self, ctx: typer.Context) -> str:
        """Get the full command path by traversing the context hierarchy."""
        command_parts = []
        current_ctx = ctx
        while current_ctx and current_ctx.parent:
            if current_ctx.command.name:
                command_parts.append(current_ctx.command.name)
            current_ctx = current_ctx.parent
        return ".".join(reversed(command_parts))

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

    def _handle_successful_logout(self, command_name: str, duration: float | None = None) -> None:
        """Handle a successful logout event.

        Upon a successful logout, we rotate the anon_id and clear the linked principal_id.
        """
        # Check if user was authenticated before logout (has linked_principal_id)
        data = self.identity.load_or_create()
        was_authenticated = data.get("linked_principal_id") is not None

        # Send logout event as the authenticated user before resetting to anonymous
        properties = {
            "command_name": command_name,
            "cli_version": self.cli_version,
            "python_version": self.python_version,
            "os_type": platform.system(),
            "os_release": platform.release(),
        }
        if duration:
            properties["duration"] = round(duration, 2)  # milliseconds

        # Check if using anon_id
        is_anon = self.user_id == self.identity.anon_id
        self.usage_service.capture(
            "CLI Command Executed", self.user_id, properties=properties, is_anon=is_anon
        )

        # Only rotate anon_id if user was actually authenticated
        if was_authenticated:
            self.identity.reset_to_anonymous()

    def track_command_execution(
        self,
        command_name: str,
        success: bool,
        duration: float | None = None,
        error_message: str | None = None,
        is_login: bool = False,
        is_logout: bool = False,
    ) -> None:
        """Track command execution event.

        Args:
            command_name: The name of the CLI command that was executed.
            success: Whether the command was successfully executed.
            duration: The duration of the command execution in milliseconds.
            error_message: The error message if the command failed.
            is_login: Whether this is a login command.
            is_logout: Whether this is a logout command.
        """
        if not is_tracking_enabled():
            return

        if is_login and success:
            self._handle_successful_login()

        elif is_logout and success:
            self._handle_successful_logout(command_name, duration)
            return

        # Edge case: Lazy alias check for other commands (if user authenticated via side path)
        elif not is_login and not is_logout and self.identity.should_alias():
            principal_id = self.identity.get_principal_id()
            if principal_id:
                self.usage_service.alias(
                    previous_id=self.identity.anon_id, distinct_id=principal_id
                )
                self.identity.set_linked_principal_id(principal_id)

        event_name = "CLI Command Executed" if success else "CLI Command Failed"

        properties = {
            "command_name": command_name,
            "cli_version": self.cli_version,
            "python_version": self.python_version,
            "os_type": platform.system(),
            "os_release": platform.release(),
        }

        if not success and error_message:
            properties["error_message"] = error_message

        if duration:
            properties["duration"] = round(duration, 2)  # milliseconds

        # Check if using anon_id (not authenticated)
        is_anon = self.user_id == self.identity.anon_id
        self.usage_service.capture(event_name, self.user_id, properties=properties, is_anon=is_anon)


# Global tracker instance
command_tracker = CommandTracker()


class TrackedTyperCommand(TyperCommand):
    """Custom TyperCommand that tracks individual command execution."""

    def invoke(self, ctx: typer.Context) -> Any:
        """Override invoke to track command execution."""
        command_name = ctx.command.name
        is_login = command_name == "login"
        is_logout = command_name == "logout"
        try:
            start_time = time.time()
            result = super().invoke(ctx)
            end_time = time.time()
            duration = end_time - start_time
            command_tracker.track_command_execution(
                command_tracker.get_full_command_path(ctx),
                success=True,
                duration=duration * 1000,
                is_login=is_login,
                is_logout=is_logout,
            )
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time

            from arcade_cli.utils import CLIError

            error_msg = str(e)[:300]
            command_tracker.track_command_execution(
                command_tracker.get_full_command_path(ctx),
                success=False,
                duration=duration * 1000,
                error_message=error_msg,
                is_login=is_login,
                is_logout=is_logout,
            )

            if isinstance(e, CLIError):
                raise typer.Exit(code=1)
            else:
                raise
        else:
            return result


class TrackedTyperGroup(TyperGroup):
    """Custom TyperGroup that creates tracked commands."""

    def command(
        self, *args, **kwargs
    ) -> Callable[[typer.models.CommandFunctionType], typer.models.CommandFunctionType]:
        """Override command decorator to use TrackedTyperCommand."""
        # Set the custom command class
        kwargs["cls"] = TrackedTyperCommand
        return super().command(*args, **kwargs)

    def list_commands(self, ctx: Context) -> list[str]:  # type: ignore[override]
        """Return list of commands in the order appear."""
        return list(self.commands)


class TrackedTyper(typer.Typer):
    """Custom Typer that creates tracked commands."""

    def command(
        self, name: str | None = None, *, cls: type[TyperCommand] | None = None, **kwargs
    ) -> Callable[[typer.models.CommandFunctionType], typer.models.CommandFunctionType]:
        """Override command decorator to use TrackedTyperCommand."""
        if cls is None:
            cls = TrackedTyperCommand

        return super().command(name, cls=cls, **kwargs)

    def callback(
        self, name: str | None = None, **kwargs
    ) -> Callable[[typer.models.CommandFunctionType], typer.models.CommandFunctionType]:
        """Override callback decorator to track callback execution."""
        original_callback_decorator = super().callback(name, **kwargs)

        def decorator(func: typer.models.CommandFunctionType) -> typer.models.CommandFunctionType:
            @functools.wraps(func)
            def tracked_callback(*args, **cb_kwargs) -> Any:
                """Wrapper that tracks callback execution."""
                # Get the context from kwargs (Typer passes it)
                ctx = cb_kwargs.get("ctx") or (
                    args[0] if args and isinstance(args[0], typer.Context) else None
                )

                command_name = ctx.invoked_subcommand if ctx and ctx.invoked_subcommand else "root"
                start_time = time.time()

                try:
                    result = func(*args, **cb_kwargs)
                except Exception as e:
                    # Track callback failure (auth failures, version checks, etc.)
                    end_time = time.time()
                    duration = (end_time - start_time) * 1000

                    from arcade_cli.utils import CLIError

                    command_tracker.track_command_execution(
                        command_name,
                        success=False,
                        duration=duration,
                        error_message=str(e)[:300],
                    )

                    if isinstance(e, CLIError):
                        raise typer.Exit(code=1)
                    else:
                        raise
                else:
                    return result

            return original_callback_decorator(tracked_callback)

        return decorator
