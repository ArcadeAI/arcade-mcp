"""Arcade refusing a sign-in because it didn't use strong authentication.

Arcade answers such a request with 401 and an RFC 9470 challenge,
``Bearer error="insufficient_user_authentication"``, whose RFC 6750
``error_description`` (and, where Arcade has one, ``error_uri``) says what to
do. The challenge is read rather than the body, because it is the same from
every Arcade service.
"""

import re
from dataclasses import dataclass

import httpx

INSUFFICIENT_USER_AUTHENTICATION = "insufficient_user_authentication"

# Shown when Arcade's refusal carries no description of its own.
STRONG_AUTHENTICATION_REQUIRED = (
    "Your organization requires a passkey or an authenticator app to sign in. "
    "Set one up in your Arcade account settings, then run 'arcade login' again."
)

# An auth-param: a token, or a quoted-string that may contain quoted-pairs
# (RFC 9110 §11.2).
_AUTH_PARAM = re.compile(r'([A-Za-z0-9_-]+)\s*=\s*(?:"((?:[^"\\]|\\.)*)"|([^\s,"]+))')
_QUOTED_PAIR = re.compile(r"\\(.)")


@dataclass(frozen=True)
class InsufficientUserAuthentication:
    """Why Arcade refused the sign-in, as its challenge describes it."""

    description: str | None
    uri: str | None


def _bearer_params(challenge: str) -> dict[str, str]:
    scheme, _, params = challenge.strip().partition(" ")
    if scheme.lower() != "bearer":
        return {}
    found: dict[str, str] = {}
    for match in _AUTH_PARAM.finditer(params):
        name, quoted, token = match.groups()
        value = _QUOTED_PAIR.sub(r"\1", quoted) if quoted is not None else token
        found.setdefault(name.lower(), value)
    return found


def from_response(response: httpx.Response) -> InsufficientUserAuthentication | None:
    """The refusal this response carries, if it is one."""
    if response.status_code != 401:
        return None
    for challenge in response.headers.get_list("www-authenticate"):
        params = _bearer_params(challenge)
        if params.get("error") == INSUFFICIENT_USER_AUTHENTICATION:
            return InsufficientUserAuthentication(
                description=params.get("error_description") or None,
                uri=params.get("error_uri") or None,
            )
    return None


def from_error(error: BaseException | None) -> InsufficientUserAuthentication | None:
    """The refusal behind an error, looking through the errors it was raised from.

    httpx's HTTPStatusError and the Arcade SDK's APIStatusError both carry the
    response they failed on; commands often wrap them before reporting.
    """
    seen: set[int] = set()
    while isinstance(error, BaseException) and id(error) not in seen:
        seen.add(id(error))
        response = getattr(error, "response", None)
        if isinstance(response, httpx.Response) and (refusal := from_response(response)):
            return refusal
        error = error.__cause__ or error.__context__
    return None
