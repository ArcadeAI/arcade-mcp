from typing import Any, Protocol, runtime_checkable

from arcadepy.types.shared import AuthorizationResponse


@runtime_checkable
class AuthCallbackProtocol(Protocol):
    def __call__(self, **kwargs: dict[str, Any]) -> AuthorizationResponse: ...
