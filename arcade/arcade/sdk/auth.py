from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class ToolAuthorization(BaseModel, ABC):
    """Marks a tool as requiring authorization."""

    @abstractmethod
    def get_provider_id(self) -> str:
        """Return the unique provider ID."""
        pass

    @abstractmethod
    def get_provider_type(self) -> str:
        """Return the type of the authorization provider."""
        pass

    pass


class OAuth2(ToolAuthorization):
    """Marks a tool as requiring OAuth 2.0 authorization."""

    provider_id: str
    """The unique provider ID configured in Arcade."""

    scopes: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""

    def get_provider_id(self) -> str:
        return self.provider_id

    def get_provider_type(self) -> str:
        return "oauth2"


class Google(OAuth2):
    """Marks a tool as requiring Google authorization."""

    def get_provider(self) -> str:
        return "google"


class Slack(OAuth2):
    """Marks a tool as requiring Slack (user token) authorization."""

    def get_provider(self) -> str:
        return "slack"


class GitHub(OAuth2):
    """Marks a tool as requiring GitHub App authorization."""

    def get_provider(self) -> str:
        return "github"


class X(OAuth2):
    """Marks a tool as requiring X (Twitter) authorization."""

    def get_provider(self) -> str:
        return "x"


class LinkedIn(OAuth2):
    """Marks a tool as requiring LinkedIn authorization."""

    def get_provider(self) -> str:
        return "linkedin"


class Spotify(OAuth2):
    """Marks a tool as requiring Spotify authorization."""

    def get_provider(self) -> str:
        return "spotify"


class Zoom(OAuth2):
    """Marks a tool as requiring Zoom authorization."""

    def get_provider(self) -> str:
        return "zoom"
