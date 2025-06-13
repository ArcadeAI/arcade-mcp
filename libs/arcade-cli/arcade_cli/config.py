"""
Configuration utilities for the Arcade CLI.
"""

from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class UserConfig:
    """User configuration."""

    email: str | None = None
    name: str | None = None


@dataclass
class ApiConfig:
    """API configuration."""

    key: str | None = None
    url: str | None = None


@dataclass
class Config:
    """Arcade CLI configuration."""

    user: UserConfig | None = None
    api: ApiConfig | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Create a Config instance from a dictionary.

        Args:
            data: Dictionary with configuration

        Returns:
            Config instance
        """
        user_data = data.get("user", {})
        api_data = data.get("api", {})

        return cls(
            user=UserConfig(
                email=user_data.get("email"),
                name=user_data.get("name"),
            ),
            api=ApiConfig(
                key=api_data.get("key"),
                url=api_data.get("url"),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to a dictionary.

        Returns:
            Configuration as a dictionary
        """
        result = {}

        if self.user:
            result["user"] = {
                "email": self.user.email,
                "name": self.user.name,
            }

        if self.api:
            result["api"] = {
                "key": self.api.key,
                "url": self.api.url,
            }

        return result


def print_config(config: dict[str, Any], name: str | None = None) -> None:
    """
    Print the configuration in a formatted table.

    Args:
        config: Configuration dictionary
        name: Optional name for the configuration
    """
    table = Table(title=f"Configuration: {name}" if name else "Configuration")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for key, value in sorted(config.items()):
        if isinstance(value, dict):
            # For nested configurations
            nested_value = "\n".join(f"{k}: {v}" for k, v in value.items())
            table.add_row(key, nested_value)
        else:
            table.add_row(key, str(value))

    console.print(table)
