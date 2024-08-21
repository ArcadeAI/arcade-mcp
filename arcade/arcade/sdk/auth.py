from abc import ABC, abstractmethod
from typing import Optional

from pydantic import AnyUrl, BaseModel


class ToolAuthorization(BaseModel, ABC):
    """Marks a tool as requiring authorization."""

    @abstractmethod
    def get_provider(self) -> str:
        """Return the name of the authorization method."""
        pass

    pass


class OAuth2(ToolAuthorization):
    """Marks a tool as requiring OAuth 2.0 authorization."""

    def get_provider(self) -> str:
        return "oauth2"

    authority: AnyUrl
    """The URL of the OAuth 2.0 authorization server."""

    scope: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""


class Google(ToolAuthorization):
    """Marks a tool as requiring Google authorization."""

    def get_provider(self) -> str:
        return "google"

    scope: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""


class SlackUser(ToolAuthorization):
    """Marks a tool as requiring Slack (user token) authorization."""

    def get_provider(self) -> str:
        return "slack_user"

    scope: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""


class GitHubApp(ToolAuthorization):
    """Marks a tool as requiring GitHub App authorization."""

    def get_provider(self) -> str:
        return "github_app"
