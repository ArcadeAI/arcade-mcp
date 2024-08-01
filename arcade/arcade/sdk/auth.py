from abc import ABC
from typing import Optional

from pydantic import AnyUrl, BaseModel


class ToolAuthorization(BaseModel, ABC):
    """Marks a tool as requiring authorization."""

    pass


class OAuth2(ToolAuthorization):
    """Marks a tool as requiring OAuth 2.0 authorization."""

    authority: AnyUrl
    """The URL of the OAuth 2.0 authorization server."""

    scope: Optional[list[str]] = None
    """The scope(s) needed for the authorized action."""
