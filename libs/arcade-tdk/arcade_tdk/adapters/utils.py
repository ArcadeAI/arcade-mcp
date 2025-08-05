from arcade_tdk.adapters import ErrorAdapter, GoogleErrorAdapter
from arcade_tdk.auth import Google, ToolAuthorization


def get_adapter_for_auth_provider(auth_provider: ToolAuthorization | None) -> ErrorAdapter | None:
    """
    Get an error adapter from an auth provider.
    """
    if not auth_provider:
        return None

    if isinstance(auth_provider, Google):
        return GoogleErrorAdapter()

    return None
