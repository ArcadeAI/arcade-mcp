from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuthProviderType(str, Enum):
    oauth2 = "oauth2"


class ToolAuthorization(BaseModel):
    """Marks a tool as requiring authorization."""

    model_config = ConfigDict(frozen=True)

    provider_id: Optional[str] = None
    """The provider ID configured in Arcade that acts as an alias to well-known configuration."""

    provider_type: AuthProviderType
    """The type of the authorization provider."""

    id: Optional[str] = None
    """A provider's unique identifier, allowing the tool to specify a specific authorization provider. Recommended for private tools only."""

    scopes: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""


class OAuth2(ToolAuthorization):
    """Marks a tool as requiring OAuth 2.0 authorization."""

    def __init__(self, *, id: str | None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes, provider_type=AuthProviderType.oauth2)


class Asana(OAuth2):
    """Marks a tool as requiring Asana authorization."""

    provider_id: str = "asana"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Atlassian(OAuth2):
    """Marks a tool as requiring Atlassian authorization."""

    provider_id: str = "atlassian"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Discord(OAuth2):
    """Marks a tool as requiring Discord authorization."""

    provider_id: str = "discord"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Dropbox(OAuth2):
    """Marks a tool as requiring Dropbox authorization."""

    provider_id: str = "dropbox"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class GitHub(OAuth2):
    """Marks a tool as requiring GitHub App authorization."""

    provider_id: str = "github"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Google(OAuth2):
    """Marks a tool as requiring Google authorization."""

    provider_id: str = "google"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Hubspot(OAuth2):
    """Marks a tool as requiring Hubspot authorization."""

    provider_id: str = "hubspot"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class LinkedIn(OAuth2):
    """Marks a tool as requiring LinkedIn authorization."""

    provider_id: str = "linkedin"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Microsoft(OAuth2):
    """Marks a tool as requiring Microsoft authorization."""

    provider_id: str = "microsoft"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Notion(OAuth2):
    """Marks a tool as requiring Notion authorization."""

    provider_id: str = "notion"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Reddit(OAuth2):
    """Marks a tool as requiring Reddit authorization."""

    provider_id: str = "reddit"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Slack(OAuth2):
    """Marks a tool as requiring Slack (user token) authorization."""

    provider_id: str = "slack"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Spotify(OAuth2):
    """Marks a tool as requiring Spotify authorization."""

    provider_id: str = "spotify"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Twitch(OAuth2):
    """Marks a tool as requiring Twitch authorization."""

    provider_id: str = "twitch"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class X(OAuth2):
    """Marks a tool as requiring X (Twitter) authorization."""

    provider_id: str = "x"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)


class Zoom(OAuth2):
    """Marks a tool as requiring Zoom authorization."""

    provider_id: str = "zoom"

    def __init__(self, *, id: Optional[str] = None, scopes: Optional[list[str]] = None):  # noqa: A002
        super().__init__(id=id, scopes=scopes)
