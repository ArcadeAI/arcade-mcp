from arcade_tdk.auth import Google, Microsoft, Slack, ToolAuthorization
from arcade_tdk.error_adapters import (
    ErrorAdapter,
    GoogleErrorAdapter,
    MicrosoftGraphErrorAdapter,
    SlackErrorAdapter,
)


def get_adapter_for_auth_provider(auth_provider: ToolAuthorization | None) -> ErrorAdapter | None:
    """
    Get an error adapter from an auth provider.
    """
    if not auth_provider:
        return None

    if isinstance(auth_provider, Google):
        return GoogleErrorAdapter()
    if isinstance(auth_provider, Microsoft):
        return MicrosoftGraphErrorAdapter()
    if isinstance(auth_provider, Slack):
        return SlackErrorAdapter()

    return None
