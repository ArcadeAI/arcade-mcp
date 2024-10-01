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
