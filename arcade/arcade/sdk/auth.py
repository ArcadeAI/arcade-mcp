from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuthProviderType(str, Enum):
    oauth2 = "oauth2"


class ToolAuthorization(BaseModel):
    """Marks a tool as requiring authorization."""

    model_config = ConfigDict(frozen=True)

    provider_id: str
    """The unique provider ID configured in Arcade."""

    provider_type: AuthProviderType
    """The type of the authorization provider."""


class OAuth2(ToolAuthorization):
    """Marks a tool as requiring OAuth 2.0 authorization."""

    provider_type: AuthProviderType = AuthProviderType.oauth2

    scopes: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""


class Google(OAuth2):
    """Marks a tool as requiring Google authorization."""

    provider_id: str = "google"


class Slack(OAuth2):
    """Marks a tool as requiring Slack (user token) authorization."""

    provider_id: str = "slack"


class GitHub(OAuth2):
    """Marks a tool as requiring GitHub App authorization."""

    provider_id: str = "github"


class X(OAuth2):
    """Marks a tool as requiring X (Twitter) authorization."""

    provider_id: str = "x"


class LinkedIn(OAuth2):
    """Marks a tool as requiring LinkedIn authorization."""

    provider_id: str = "linkedin"


class Spotify(OAuth2):
    """Marks a tool as requiring Spotify authorization."""

    provider_id: str = "spotify"


class Zoom(OAuth2):
    """Marks a tool as requiring Zoom authorization."""

    provider_id: str = "zoom"
