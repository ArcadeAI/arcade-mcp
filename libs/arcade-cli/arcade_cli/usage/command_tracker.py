import sys
from importlib import metadata
from typing import Any, Callable

import typer
from arcade_cli.usage.usage_service import UsageService
from typer.core import TyperCommand, TyperGroup
from typer.models import Context


class CommandTracker:
    """Tracks CLI command execution for usage analytics."""

    def __init__(self) -> None:
        self.usage_service = UsageService()
        self._cli_version = None
        self._python_version = None

    @property
    def cli_version(self) -> str:
        """Get CLI version, cached after first access."""
        if self._cli_version is None:
            try:
                self._cli_version = metadata.version("arcade-ai")
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

    def get_mock_user_id(self) -> str:
        """Get mock user ID. TODO: Replace with actual user ID from config."""
        return "mock_user_123"

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
        error_message: str | None = None,
    ) -> None:
        """Track command execution event."""
        event_name = "CLI Command Executed" if success else "CLI Command Failed"

        properties = {
            "command_name": command_name,
            "cli_version": self.cli_version,
            "python_version": self.python_version,
            "user_id": self.get_mock_user_id(),
        }

        if not success and error_message:
            properties["error_message"] = error_message

        self.usage_service.capture(event_name, properties)


# Global tracker instance
command_tracker = CommandTracker()


class TrackedTyperCommand(TyperCommand):
    """Custom TyperCommand that tracks individual command execution."""

    def invoke(self, ctx: typer.Context) -> Any:
        """Override invoke to track command execution."""
        try:
            result = super().invoke(ctx)
            print(f"DEBUG - Command name: {ctx.command.name}")
            command_tracker.track_command_execution(
                command_tracker.get_full_command_path(ctx), success=True
            )
        except Exception as e:
            error_msg = str(e)[:200]
            command_tracker.track_command_execution(
                command_tracker.get_full_command_path(ctx),
                success=False,
                error_message=error_msg,
            )
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
        return list(self.commands)  # get commands using self.commands


class TrackedTyper(typer.Typer):
    """Custom Typer that creates tracked commands."""

    def command(
        self, name: str | None = None, *, cls: type[TyperCommand] | None = None, **kwargs
    ) -> Callable[[typer.models.CommandFunctionType], typer.models.CommandFunctionType]:
        """Override command decorator to use TrackedTyperCommand."""
        if cls is None:
            cls = TrackedTyperCommand

        return super().command(name, cls=cls, **kwargs)
