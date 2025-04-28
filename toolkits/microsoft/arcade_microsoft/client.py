import datetime
from typing import Any

from azure.core.credentials import AccessToken, TokenCredential
from msgraph import GraphServiceClient

DEFAULT_SCOPE = "https://graph.microsoft.com/.default"


class StaticTokenCredential(TokenCredential):
    """Implementation of TokenCredential protocol to be provided to the MSGraph SDK client"""

    def __init__(self, token: str):
        self._token = token

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        # An expiration is required by MSGraph SDK. Set to 1 hour from now.
        expires_on = int(datetime.datetime.now(datetime.timezone.utc).timestamp()) + 3600
        return AccessToken(self._token, expires_on)


def get_client(token: str) -> GraphServiceClient:
    """Create and return a MSGraph SDK client, given the provided token."""
    token_credential = StaticTokenCredential(token)

    return GraphServiceClient(token_credential, scopes=[DEFAULT_SCOPE])
