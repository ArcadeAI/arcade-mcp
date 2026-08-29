from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

import httpx

from arcade_core.schema import ToolContext

T = TypeVar("T")

PROTECTED_API_METADATA_NAMESPACE = "arcade.token_exchange.v1"


class ProtectedAPIOutcome(str, Enum):
    """Private authorization outcome for one protected API request."""

    ACCEPTED = "accepted"
    AUTHORIZATION_DENIED = "authorization_denied"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProtectedAPIResult(Generic[T]):
    """A protected API value paired with its private authorization outcome."""

    value: T | None
    outcome: ProtectedAPIOutcome


def _result(
    context: ToolContext,
    value: T | None,
    outcome: ProtectedAPIOutcome,
) -> ProtectedAPIResult[T]:
    context.protected_api_outcome = outcome.value
    return ProtectedAPIResult(value=value, outcome=outcome)


def build_protected_api_metadata(outcome: str | None) -> dict[str, dict[str, str]] | None:
    """Build the versioned wire metadata for one allowlisted outcome."""

    if outcome is None:
        return None
    try:
        protected_api_outcome = ProtectedAPIOutcome(outcome)
    except ValueError:
        return None
    return {
        PROTECTED_API_METADATA_NAMESPACE: {
            "protected_api_outcome": protected_api_outcome.value,
        }
    }


async def call_protected_api(
    context: ToolContext,
    method: str,
    url: str,
    *,
    timeout: float,
    headers: Mapping[str, str] | None = None,
    params: Mapping[str, str] | None = None,
    json_body: Any = None,
) -> ProtectedAPIResult[Any]:
    """Make one authenticated request and return a fixed private outcome.

    The adapter never retries and never returns authorization or transport
    response bodies for denied or unavailable requests.
    """

    token = context.get_auth_token_or_empty()
    if not token:
        raise ValueError("protected API calls require an authorization token")

    request_headers = dict(headers or {})
    if any(key.lower() == "authorization" for key in request_headers):
        raise ValueError("protected API authorization is supplied by the tool context")
    request_headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.request(
                method,
                url,
                headers=request_headers,
                params=params,
                json=json_body,
            )
    except (httpx.RequestError, httpx.InvalidURL):
        return _result(context, None, ProtectedAPIOutcome.UNAVAILABLE)

    if response.status_code in (401, 403):
        return _result(context, None, ProtectedAPIOutcome.AUTHORIZATION_DENIED)
    if not 200 <= response.status_code < 300:
        return _result(context, None, ProtectedAPIOutcome.UNAVAILABLE)

    try:
        value = response.json()
    except ValueError:
        value = response.text
    return _result(context, value, ProtectedAPIOutcome.ACCEPTED)
