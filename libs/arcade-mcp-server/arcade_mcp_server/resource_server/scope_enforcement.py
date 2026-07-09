"""Public scope-enforcement helper for MCP Resource Servers."""

from collections.abc import Iterable
from typing import Any

from starlette.types import Scope

from arcade_mcp_server.resource_server.base import (
    InsufficientScopeError,
    ResourceOwner,
)
from arcade_mcp_server.resource_server.middleware import RESOURCE_OWNER_SCOPE_KEY


def enforce_scopes(scope: Scope, required: Iterable[str]) -> None:
    """Assert the request's resource owner has every required OAuth scope.

    Reads ``ResourceOwner`` from ``scope[RESOURCE_OWNER_SCOPE_KEY]``
    (populated by ``ResourceServerMiddleware``). If any required
    scope is missing from ``resource_owner.granted_scopes``, raises
    ``InsufficientScopeError`` carrying the FULL caller-supplied
    ``required`` list (in caller order), NOT the missing subset.
    Per the MCP authorization spec (Runtime Insufficient Scope
    Errors), the 403 ``WWW-Authenticate: scope=`` parameter
    advertises the operation's required scopes; it is the client's
    job to step up to that full set, not to guess which subset the
    server "actually" needs. ``granted_scopes`` on the raised
    exception is diagnostic-only metadata (caller logs, elevation
    telemetry) and is intentionally NOT emitted into the 403 header.

    Raises:
        RuntimeError: if ``resource_owner`` is absent (middleware not
            installed, or request did not pass token validation).
        InsufficientScopeError: if any required scope is missing.
    """
    resource_owner: Any = scope.get(RESOURCE_OWNER_SCOPE_KEY)
    if not isinstance(resource_owner, ResourceOwner):
        # RuntimeError is intentional: this is not a wrong-type bug at
        # the call site (the call signature is ``Scope, Iterable[str]``
        # and is satisfied), it is a runtime-configuration failure where
        # ResourceServerMiddleware never populated the ASGI scope. A
        # TypeError would mislead the caller into checking their args.
        raise RuntimeError(  # noqa: TRY004
            "enforce_scopes called on a request without a resource_owner. "
            "ResourceServerMiddleware must be installed and the request "
            "must have passed Bearer-token validation."
        )

    # Materialize once: ``required`` may be a generator. Build the
    # frozenset from the materialized list, NOT from ``required``
    # directly, because doing the latter would exhaust the generator.
    required_list = list(required)
    required_set = frozenset(required_list)
    if not required_set.issubset(resource_owner.granted_scopes):
        raise InsufficientScopeError(
            required_scopes=required_list,
            granted_scopes=resource_owner.granted_scopes,
        )
