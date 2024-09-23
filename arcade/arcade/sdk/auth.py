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


class BaseOAuth2(ToolAuthorization):
    """Base class for any provider supporting OAuth 2.0-like authorization."""

    authority: Optional[AnyUrl] = None
    """The URL of the OAuth 2.0 authorization server."""

    scopes: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""


class OAuth2(BaseOAuth2):
    """Marks a tool as requiring OAuth 2.0 authorization."""

    def get_provider(self) -> str:
        return "oauth2"


class Google(BaseOAuth2):
    """Marks a tool as requiring Google authorization."""

    def get_provider(self) -> str:
        return "google"


class SlackUser(BaseOAuth2):
    """Marks a tool as requiring Slack (user token) authorization."""

    def get_provider(self) -> str:
        return "slack_user"


class GitHubApp(ToolAuthorization):
    """Marks a tool as requiring GitHub App authorization."""

    def get_provider(self) -> str:
        return "github_app"


class X(BaseOAuth2):
    """Marks a tool as requiring X (Twitter) authorization."""

    def get_provider(self) -> str:
        return "x"
