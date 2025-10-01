import platform
import sys
import time
from importlib import metadata
from typing import Any, Callable

import typer
from arcade_cli.usage.identity import UsageIdentity
from arcade_cli.usage.usage_service import UsageService
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
        # Handle login success
        if is_login and success:
            email = self.identity.get_email()
            if email and self.identity.should_alias():
                # Try both methods to ensure linking works for all users:
                # 1. alias() - works for new users without merge restrictions
                self.usage_service.alias(previous_id=self.identity.anon_id, distinct_id=email)
                # 2. merge_dangerously() - works for existing users with merge restrictions
                self.usage_service.merge_dangerously(
                    distinct_id=email, anon_distinct_id=self.identity.anon_id
                )
                self.identity.set_linked_email(email)

        # Handle logout success
        elif is_logout and success:
            # Only rotate anon_id if user was actually authenticated
            was_authenticated = self.identity.get_email() is not None

            # Send event with current user_id before rotating
            event_name = "CLI Command Executed" if success else "CLI Command Failed"
            properties = {
                "command_name": command_name,
                "cli_version": self.cli_version,
                "python_version": self.python_version,
                "os_type": platform.system(),
                "os_release": platform.release(),
            }
            if duration:
                properties["duration"] = round(duration, 2)  # milliseconds
            self.usage_service.capture(event_name, self.user_id, properties=properties)

            # Only rotate anon_id if user was authenticated (prevents unnecessary rotation)
            if was_authenticated:
                self.identity.rotate_anon_id()
            return

        # Edge case: Lazy alias check for other commands (if user authenticated via side path)
        elif not is_login and not is_logout and self.identity.should_alias():
            self.usage_service.alias(
                previous_id=self.identity.anon_id, distinct_id=self.identity.get_email()
            )
            self.identity.set_linked_email(self.identity.get_email())

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

        self.usage_service.capture(event_name, self.user_id, properties=properties)


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
            error_msg = str(e)[:200]
            command_tracker.track_command_execution(
                command_tracker.get_full_command_path(ctx),
                success=False,
                error_message=error_msg,
                is_login=is_login,
                is_logout=is_logout,
            )
            raise
        else:
            print(
                f"[TrackedTyperCommand] Command {ctx.command.name} executed with result: {result}"
            )
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
