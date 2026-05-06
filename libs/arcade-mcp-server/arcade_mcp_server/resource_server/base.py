"""Base classes for MCP Resource Server authentication."""

import logging
import re
import urllib.parse
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# RFC 6750 scope-token ABNF: 1*( %x21 / %x23-5B / %x5D-7E )
# Equivalent to: at least one printable ASCII character, excluding ``"``
# (0x22), ``\`` (0x5C), space, control characters (< 0x20 and 0x7F), and any
# non-ASCII character.
_VALID_SCOPE_TOKEN = re.compile(r"^[\x21\x23-\x5B\x5D-\x7E]+$")
_WHITESPACE = re.compile(r"\s")

# RFC 6750 Section 3 ABNF for Bearer auth-param values:
#   error-char = %x20-21 / %x23-5B / %x5D-7E
# The set excludes DQUOTE (0x22), backslash (0x5C), HTAB (0x09),
# CR (0x0D), LF (0x0A), other CTLs (0x00-0x1F, 0x7F), and
# non-ASCII (0x80+). RFC 6750 does NOT permit quoted-pair
# escaping inside ``error_description``, ``error``, or ``scope``
# values; a violating character is a flat reject, never an
# escape opportunity. The char grammar is necessary but NOT
# sufficient for ``resource_metadata`` URIs: the grammar permits
# unencoded space and many bytes that a well-formed RFC 3986
# URI never contains, so URIs need a structural check
# (``_validate_resource_metadata_url`` below) on top of the
# bare char grammar.
_RFC6750_QUOTED_VALUE_FORBIDDEN = re.compile(r"[^\x20-\x21\x23-\x5B\x5D-\x7E]")

# Loopback hosts permitted to use the ``http`` scheme on canonical URLs.
# RFC 8252 Section 7.3 enumerates loopback redirect URIs as
# ``http://127.0.0.1`` and ``http://[::1]``; OAuth 2.1 draft Section 8.4.2
# carries the rule forward. Mainstream OAuth toolkits accept ``localhost``
# as well via OS convention. ``urlsplit().hostname`` lowercases the host
# and strips IPv6 brackets, so ``[::1]`` arrives as ``::1`` and
# ``LocalHost`` arrives as ``localhost`` before the membership check.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

# RFC 3986 ``pct-encoded = "%" HEXDIG HEXDIG``. ``urlsplit`` does not
# validate percent-escapes. ``%`` followed by fewer than two hex digits
# (or non-hex bytes) is invalid in any URI component.
_MALFORMED_PERCENT_ESCAPE = re.compile(r"%(?![0-9A-Fa-f]{2})")

# RFC 3986 forbids unencoded whitespace in any URI component. The bare
# RFC 6750 char grammar permits 0x20 (space), so this layer is necessary
# in addition to ``_RFC6750_QUOTED_VALUE_FORBIDDEN``.
_UNENCODED_WHITESPACE = re.compile(r"\s")


def _validate_rfc6750_quoted_value(value: str) -> str:
    """Validate a Bearer auth-param value against RFC 6750 ``error-char``.

    Returns ``value`` unchanged when valid. Raises ``ValueError``
    with a precise classification when ``value`` contains a
    forbidden character (DQUOTE, backslash, HTAB, CR, LF, other
    CTLs, non-ASCII).

    Use for any Bearer auth-param value emitted into a
    ``WWW-Authenticate`` header: ``error_description``, ``error``,
    and ``resource_metadata`` URI. RFC 6750 does not permit
    escaping inside these values, so reject is the only conformant
    handling. ``scope`` values are validated more strictly via
    ``_validate_scope_token`` per RFC 6749 ``scope-token`` grammar
    (a strict subset of ``error-char``); the joined ``scope=``
    string therefore needs no second pass.
    """
    match = _RFC6750_QUOTED_VALUE_FORBIDDEN.search(value)
    if match is not None:
        raise ValueError(
            f"Value contains a character forbidden in RFC 6750 "
            f"auth-param value (offset {match.start()}, codepoint "
            f"U+{ord(match.group()):04X}): {value!r}"
        )
    return value


def _sanitize_rfc6750_quoted_value(value: str, *, field: str) -> str | None:
    """Sanitize-and-omit variant of ``_validate_rfc6750_quoted_value``.

    Returns ``value`` when it conforms to the RFC 6750 ``error-char``
    grammar. Returns ``None`` and logs a warning when ``value`` would
    corrupt a ``WWW-Authenticate`` header parameter (DQUOTE, backslash,
    HTAB, CR, LF, other CTLs, non-ASCII).

    Use at emit sites where a spec MUST forces the response to be
    returned even when a downstream input is non-conformant: the 401
    path is the canonical case. The MCP authorization spec section
    Resource Server Responsibilities mandates HTTP 401 for invalid
    Bearer tokens, so a non-conformant ``error_description`` from an
    upstream validator (pyjwt, custom IdP integrations, localized
    error messages with non-ASCII bytes) must never block the 401
    response. Sanitize-and-omit preserves the spec MUST while still
    refusing to corrupt the header line. ``field`` is included in
    the log line so operators can pinpoint which upstream emitted
    the offending value.
    """
    match = _RFC6750_QUOTED_VALUE_FORBIDDEN.search(value)
    if match is None:
        return value
    logger.warning(
        "Dropping non-conformant RFC 6750 auth-param value for %s "
        "(offset %d, codepoint U+%04X). The 401 response is still "
        "returned with the parameter omitted.",
        field,
        match.start(),
        ord(match.group()),
    )
    return None


def _validate_resource_metadata_url(value: str) -> str:
    """Validate a canonical URL or PRM resource_metadata URL.

    Four layers of enforcement applied in order:

    1. RFC 6750 ``error-char`` (no DQUOTE / backslash / HTAB / CR / LF
       / CTLs / non-ASCII): a header injection guard. ``error-char``
       permits printable ASCII including unencoded space, which a
       well-formed RFC 3986 URI never contains, so passing the char
       grammar alone does NOT prove URI validity.

    2. RFC 3986 URI structure plus RFC 9728 scheme rule with a
       documented loopback exception:

       - ``netloc`` is non-empty (a non-URI like ``"hello world"``
         passes the char grammar but is not a URL).
       - ``scheme`` is ``https`` for any non-loopback host. RFC 9728
         Section 2 defines the protected-resource identifier as a URL
         using the ``https`` scheme.
       - ``http`` is permitted only when the host (after
         case-folding and IPv6-bracket stripping by
         ``urlsplit().hostname``) is in ``_LOOPBACK_HOSTS``:
         ``127.0.0.1``, ``::1``, ``localhost``. RFC 8252 Section 7.3
         and OAuth 2.1 draft Section 8.4.2 carry the rule.

    3. RFC 3986 character correctness:

       - No unencoded whitespace anywhere in the URL.
       - Every ``%`` is followed by exactly two hex digits.

    4. MCP canonical-URI rule: the URL MUST NOT contain a fragment
       component. The MCP 2025-11-25 authorization spec section
       Canonical Server URI explicitly rejects fragments; RFC 8707
       Section 2 forbids them in the resource identifier. Query
       components are permitted (RFC 8707: "Query components MUST
       be retained when used"), so this check rejects fragments only.

    Returns ``value`` unchanged when all four layers pass. Raises
    ``ValueError`` with a precise classification on failure.
    """
    _validate_rfc6750_quoted_value(value)
    parsed = urllib.parse.urlsplit(value)
    if not parsed.netloc:
        raise ValueError(
            f"Canonical URL must have a non-empty host, got " f"empty netloc: {value!r}"
        )
    if parsed.scheme == "https":
        pass
    elif parsed.scheme == "http":
        host = parsed.hostname
        if host not in _LOOPBACK_HOSTS:
            raise ValueError(
                f"Canonical URL must use https for non-loopback "
                f"hosts (RFC 9728 Section 2). http is permitted "
                f"only for loopback hosts "
                f"({sorted(_LOOPBACK_HOSTS)}, RFC 8252 "
                f"Section 7.3); got host {host!r}: {value!r}"
            )
    else:
        raise ValueError(
            f"Canonical URL must use https scheme (or http for "
            f"loopback hosts {sorted(_LOOPBACK_HOSTS)}); got "
            f"scheme {parsed.scheme!r}: {value!r}"
        )
    ws_match = _UNENCODED_WHITESPACE.search(value)
    if ws_match is not None:
        raise ValueError(
            f"Canonical URL must not contain unencoded whitespace "
            f"(RFC 3986); first whitespace at offset "
            f"{ws_match.start()}: {value!r}"
        )
    pct_match = _MALFORMED_PERCENT_ESCAPE.search(value)
    if pct_match is not None:
        raise ValueError(
            f"Canonical URL contains a malformed percent-escape "
            f"(RFC 3986 ``pct-encoded`` requires two hex digits "
            f"after each ``%``); first malformed escape at offset "
            f"{pct_match.start()}: {value!r}"
        )
    if parsed.fragment:
        raise ValueError(
            f"Canonical URL must not contain a fragment component "
            f"(MCP 2025-11-25 spec section Canonical Server URI; "
            f"RFC 8707 Section 2 forbids fragments in the resource "
            f"identifier). Got fragment {parsed.fragment!r}: {value!r}"
        )
    if "#" in value:
        # ``urlsplit`` reports an empty fragment for a trailing bare
        # ``#``, which is still a fragment delimiter. Reject loudly.
        raise ValueError(
            f"Canonical URL must not contain a fragment delimiter "
            f"'#' (MCP 2025-11-25 spec section Canonical Server URI): "
            f"{value!r}"
        )
    return value


def _validate_scope_token(token: str) -> None:
    """Validate a single scope token against the RFC 6750 grammar.

    The grammar is ``scope-token = 1*( %x21 / %x23-5B / %x5D-7E )`` — at
    least one printable ASCII character, excluding ``"``, ``\\``, space,
    control characters, and non-ASCII.

    Validation runs at ``ResourceServerAuth`` construction (and at env-var
    parse time) so malformed tokens fail fast with a precise error rather
    than silently corrupting the ``WWW-Authenticate`` header at runtime.

    Args:
        token: A single OAuth scope value.

    Raises:
        ValueError: with a message classifying the failure (empty,
        whitespace, non-ASCII, or RFC 6750 grammar violation) and naming
        the offending token.
    """
    if not token:
        raise ValueError("Scope token must not be empty")
    if not token.strip():
        raise ValueError(f"Scope token must not be empty or whitespace-only: {token!r}")
    if _WHITESPACE.search(token):
        raise ValueError(f"Scope token must not contain whitespace per RFC 6750: {token!r}")
    try:
        token.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"Scope token must be ASCII (non-ASCII char in {token!r}): {exc}") from exc
    if not _VALID_SCOPE_TOKEN.match(token):
        raise ValueError(
            f"Scope token violates RFC 6750 grammar: {token!r}. "
            'Allowed: 0x21 / 0x23-0x5B / 0x5D-0x7E (no spaces, ", \\, '
            "control chars, or non-ASCII)."
        )


def _validate_advertised_scopes(scopes: list[str] | None) -> list[str] | None:
    """Validate, deduplicate, and normalize a list of OAuth scope tokens.

    Each token must conform to the RFC 6750 grammar (see
    ``_validate_scope_token``). Duplicates are removed with first-seen
    ordering preserved — operators expect their declared order to drive the
    advertised order in PRM ``scopes_supported`` and on the
    ``WWW-Authenticate`` ``scope`` parameter.

    Args:
        scopes: Scope token list (as passed to ``scopes_supported`` or
            ``default_challenge_scopes``) or ``None``.

    Returns:
        Validated, deduplicated list (first-seen order), or ``None`` if
        input was ``None`` or empty list (signaling "no advertisement").

    Raises:
        ValueError: If any token violates the RFC 6750 grammar.
    """
    if not scopes:
        return None
    for token in scopes:
        _validate_scope_token(token)
    return list(dict.fromkeys(scopes))


class AccessTokenValidationOptions(BaseModel):
    """Options for access token validation.

    All validations are enabled by default for security.
    Set to False to disable specific validations for authorization servers
    that are not compliant with MCP.

    Note: Token signature verification and audience validation are always enabled
    and cannot be disabled. Additionally, the subject (sub claim) must always be
    present in the token.
    """

    verify_exp: bool = Field(
        default=True,
        description="Verify token expiration (exp claim)",
    )
    verify_iat: bool = Field(
        default=True,
        description="Verify issued-at time (iat claim)",
    )
    verify_iss: bool = Field(
        default=True,
        description="Verify issuer claim (iss claim)",
    )
    verify_nbf: bool = Field(
        default=True,
        description="Verify not-before time (nbf claim). Rejects tokens used before their activation time.",
    )
    leeway: int = Field(
        default=0,
        description="Clock skew tolerance in seconds for exp/nbf validation. Recommended: 30-60 seconds.",
    )


@dataclass
class ResourceOwner:
    """User information extracted from validated access token.

    This represents the authenticated resource owner (end-user) making requests
    to the MCP server. The user_id typically comes from the 'sub' (subject) claim
    in JWT tokens.
    """

    user_id: str
    """User identifier from token (typically 'sub' claim)"""

    client_id: str | None = None
    """OAuth client identifier from 'client_id' or 'azp' claim"""

    email: str | None = None
    """User email if available in token claims"""

    granted_scopes: frozenset[str] = field(default_factory=frozenset)
    """OAuth scopes granted by the validated access token. Auto-populated
    by ``validate_token`` from the JWT ``scope`` claim (RFC 8693 OAuth-
    canonical, space-separated string) or ``scp`` claim (vendor variant,
    list). Empty frozenset if neither is present or both are malformed.
    ``frozenset`` because downstream code performs subset checks."""

    claims: dict[str, Any] = field(default_factory=dict)
    """All claims from the validated token for advanced use cases"""


@dataclass
class AuthorizationServerEntry:
    """Configuration entry for a single authorization server.

    Each authorization server that can issue valid tokens for this
    MCP server (Resource Server) needs its own entry specifying how to
    verify tokens from that server.
    """

    authorization_server_url: str
    """Authorization server URL for client discovery (RFC 9728)"""

    issuer: str
    """Expected issuer claim in JWT tokens from this server"""

    jwks_uri: str
    """JWKS endpoint to fetch public keys for token verification"""

    algorithm: str = "RS256"
    """JWT signature algorithm (RS256, ES256, PS256, etc.)"""

    expected_audiences: list[str] | None = None
    """Optional list of expected audience claims. If not provided,
    defaults to the MCP server's canonical_url. Use this when your
    authorization server returns a different aud claim (e.g., client_id)."""

    validation_options: AccessTokenValidationOptions = field(
        default_factory=AccessTokenValidationOptions
    )
    """Token validation options for this authorization server"""


class AuthenticationError(Exception):
    """Base authentication error."""

    pass


class TokenExpiredError(AuthenticationError):
    """Token has expired."""

    pass


class InvalidTokenError(AuthenticationError):
    """Token is invalid (signature, audience, issuer, etc.)."""

    pass


class InsufficientScopeError(Exception):
    """RFC 6750 ``insufficient_scope`` error.

    Subclasses ``Exception`` directly (NOT ``AuthenticationError``):
    400-class auth errors are the 401 path; insufficient_scope is the
    403 path. Conflating would re-emit ``invalid_token`` headers.

    ``required_scopes`` is the only field the middleware emits into
    the 403 ``WWW-Authenticate: scope="..."`` parameter. Per the MCP
    authorization spec (Runtime Insufficient Scope Errors / Server
    Scope Management "minimum approach"), the header advertises
    the operation's required minimum, NOT the full token grant.
    ``granted_scopes`` is diagnostic-only metadata (caller logging,
    future elevation tooling); it is intentionally NOT echoed into
    the header. Leaking unrelated granted scopes contradicts the
    MCP security best practices' Scope Minimization guidance ("emit
    precise scope challenges; avoid returning the full catalog").
    """

    def __init__(
        self,
        required_scopes: Iterable[str],
        granted_scopes: Iterable[str] = (),
        error_description: str | None = None,
    ) -> None:
        required_tuple = tuple(required_scopes)
        granted_frozenset = frozenset(granted_scopes)
        # Validate BOTH against RFC 6749 ``scope-token`` grammar.
        # ``required`` reaches the WWW-Authenticate header directly;
        # ``granted`` is diagnostic today but future code paths may
        # surface it, and base.py warns malformed tokens corrupt
        # WWW-Authenticate. Defense-in-depth at the construction
        # boundary catches manual / test misuse.
        for token in required_tuple:
            _validate_scope_token(token)
        for token in granted_frozenset:
            _validate_scope_token(token)
        # Validate ``error_description`` against RFC 6750 ``error-char``
        # grammar at construction. RFC 6750 forbids DQUOTE, backslash,
        # HTAB, CR, LF, other CTLs, and non-ASCII inside
        # ``error_description`` and does NOT permit quoted-pair
        # escaping; a violating character is a flat reject, not an
        # escape opportunity. Validating at construction fails fast
        # for misuse instead of silently producing a malformed header
        # at request time. The middleware re-runs the same validator
        # at emit time as defense-in-depth. The validator returns the
        # value unchanged when valid, so the in-memory exception field
        # stays human-readable for logs and ``__str__``.
        if error_description is not None:
            _validate_rfc6750_quoted_value(error_description)
        self.required_scopes = required_tuple
        self.granted_scopes = granted_frozenset
        self.error_description = error_description
        super().__init__(
            f"Insufficient scope: required={list(required_tuple)}, "
            f"granted={sorted(self.granted_scopes)}"
        )


class ResourceServerValidator(ABC):
    """Base class for MCP Resource Server token validation.

    An MCP server acts as an OAuth 2.1 Resource Server, validating Bearer tokens
    on every HTTP request. Implementations must validate tokens according to
    OAuth 2.1 Resource Server requirements, including:
    - Token signature verification
    - Expiration checking
    - Issuer validation
    - Audience validation

    Tokens are validated on every request, no caching is permitted per MCP spec.

    The MCP 2025-11-25 spec (driven by SEP-835) treats two scope surfaces as
    independent:

    - PRM ``scopes_supported`` (RFC 9728): discoverable advertisement, the
      *minimum baseline* for basic functionality.
    - ``WWW-Authenticate: scope=`` (RFC 6750): what the server is challenging
      the client to acquire RIGHT NOW.

    Subclasses set ``scopes_supported`` and ``default_challenge_scopes`` in
    ``__init__`` to populate the two surfaces. They are independent: a
    challenge MAY be a subset, superset, or alternative collection of PRM.
    ``ResourceServerMiddleware`` reads ``default_challenge_scopes`` directly
    from the validator for the entry-401 challenge; the PRM document is
    populated from ``scopes_supported``. Both attributes live on the ABC
    contract so middleware does not need defensive ``getattr``.
    """

    scopes_supported: list[str] | None = None
    """Operator-declared scopes for RFC 9728 PRM ``scopes_supported``.
    Per the MCP spec, the *minimum* scopes for basic functionality. ``None``
    omits the field from PRM. Independent of ``default_challenge_scopes``.

    The class-level default is ``None`` (immutable) rather than ``[]`` to
    avoid the mutable-default-argument footgun: a list at the class level
    would be shared across all subclass instances and could leak state via
    ``self.scopes_supported.append(...)``. ``None`` is always shadowed
    cleanly by subclass instance assignment.
    """

    default_challenge_scopes: list[str] | None = None
    """Operator-declared scopes for the entry-401 RFC 6750
    ``WWW-Authenticate: scope=`` parameter. ``None`` omits ``scope=``.
    Independent of ``scopes_supported``: the spec explicitly permits
    this set to be a non-subset / non-superset alternative collection.

    Same class-level immutability rationale as ``scopes_supported``.
    """

    @abstractmethod
    async def validate_token(self, token: str) -> ResourceOwner:
        """Validate bearer token and return authenticated resource owner info.

        Must validate:
        - Token signature
        - Expiration
        - Issuer (matches expected authorization server)
        - Audience (matches this MCP server's canonical URL)

        Args:
            token: Bearer token from Authorization header

        Returns:
            ResourceOwner with user_id and claims

        Raises:
            TokenExpiredError: Token has expired
            InvalidTokenError: Token is invalid (signature, audience, issuer mismatch)
            AuthenticationError: Other validation errors
        """
        pass

    def supports_oauth_discovery(self) -> bool:
        """Whether this validator supports OAuth discovery endpoints.

        Returns True if the validator can serve OAuth 2.0 Protected Resource Metadata
        (RFC 9728) to enable MCP clients to discover authorization servers.
        """
        return False

    def get_resource_metadata(self) -> dict[str, Any] | None:
        """Return OAuth Protected Resource Metadata (RFC 9728) if supported.

        Returns:
            Metadata dictionary with 'resource' and 'authorization_servers' fields,
            or None if discovery is not supported.
        """
        return None
