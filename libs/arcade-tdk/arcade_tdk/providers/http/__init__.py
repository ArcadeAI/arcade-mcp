"""
TODO: This imports the whole httpx package which will
      add a startup cost and pull in dozens of submodules immediately.
      We should consider using a helper for 'soft imports'.

A soft import could look something like this:

# arcade_tdk/utils/imports.py
import importlib

def require_extra(module: str, extra: str):
    try:
        return importlib.import_module(module)
    except ImportError as e:
        raise ImportError(
            f"The '{extra}' extra is required to use this adapter. "
            f"Install it with: pip install 'arcade-tdk[{extra}]'"
        ) from e


# arcade_tdk/adapters/msgraph/client.py
from arcade_tdk.utils.imports import require_extra

def translate_msgraph_error(err):
    msgraph_sdk = require_extra("msgraph_sdk", "msgraph")
    ...
"""

try:
    import httpx  # noqa: F401
except ImportError as e:
    raise ImportError(
        "The 'http' adapter requires the 'http' extra. "
        "Install it with: pip install 'arcade-tdk[http]'"
    ) from e


from arcade_tdk.providers.http.error_adapter import HTTPErrorAdapter

__all__ = ["HTTPErrorAdapter"]
