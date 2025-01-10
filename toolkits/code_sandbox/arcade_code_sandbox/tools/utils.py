import os
from typing import Any, Optional


def get_secret(name: str, default: Optional[Any] = None) -> Any:
    secret = os.getenv(name)
    if secret is None and default is not None:
        return default
    return secret
