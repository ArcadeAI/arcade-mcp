"""Shared WWW-Authenticate construction helpers.

Exposed to both ``middleware._create_403_insufficient_scope_response``
and ``MCPServer._handle_call_tool``'s inline JSON-RPC 403 path so the
two emit sites produce byte-identical headers for the same inputs.
The inline path keeps the JSON-RPC framing (the ``_transport``
metadata bridge in ``http_streamable.py`` already converts the
``JSONRPCError`` to HTTP 403 + header); only the header *string*
construction is shared.
"""

from collections.abc import Iterable

from arcade_mcp_server.resource_server.base import (
    _validate_resource_metadata_url,
    _validate_rfc6750_quoted_value,
    _validate_scope_token,
)


def build_insufficient_scope_www_authenticate(
    *,
    required_scopes: Iterable[str],
    resource_metadata_url: str | None,
    error_description: str | None = None,
) -> str:
    """Build the ``WWW-Authenticate`` value for a 403 insufficient_scope.

    Order: ``resource_metadata`` (if provided), ``error="insufficient_scope"``,
    ``scope="..."`` (if non-empty), ``error_description="..."`` (if provided).
    The order matches the MCP authorization spec example.

    Validation discipline at the helper boundary:

    - Each ``required_scopes`` token runs through ``_validate_scope_token``
      (RFC 6749 ``scope-token`` grammar). The inline JSON-RPC 403 path in
      ``MCPServer._handle_call_tool`` reads scopes directly from
      ``ToolAuthorization.scopes``, which today has no grammar validation
      at the tool-decorator boundary; a tool author writing
      ``@tool(requires_auth=Provider(scopes=["bad token"]))`` would
      otherwise corrupt the ``WWW-Authenticate`` header on the inline
      path because that path bypasses ``InsufficientScopeError.__init__``
      entirely. Validating here closes the gap.
    - ``resource_metadata_url`` runs through ``_validate_resource_metadata_url``
      (RFC 6750 ``error-char`` AND RFC 3986 URI structure: scheme is
      http/https, netloc is non-empty, no whitespace, no malformed
      percent-escapes, no fragment). The bare char grammar permits
      spaces and many bytes that a well-formed URI never contains, so
      URI structural validation is required to prevent a misconfigured
      ``MCP_RESOURCE_SERVER_CANONICAL_URL`` from propagating a non-URI
      string into the ``resource_metadata=`` param.
    - ``error_description`` runs through ``_validate_rfc6750_quoted_value``
      (RFC 6750 ``error-char`` grammar). ASCII-printable descriptions
      pass unchanged; malformed input raises ``ValueError`` rather
      than silently corrupting the header.

    Raises:
        ValueError: when any ``required_scopes`` token violates the
            RFC 6749 ``scope-token`` grammar, when
            ``resource_metadata_url`` violates the RFC 6750 char
            grammar OR the URI structure, or when ``error_description``
            violates the RFC 6750 char grammar.
    """
    required_list = list(required_scopes)
    for token in required_list:
        _validate_scope_token(token)
    parts: list[str] = []
    if resource_metadata_url:
        validated_url = _validate_resource_metadata_url(resource_metadata_url)
        parts.append(f'resource_metadata="{validated_url}"')
    parts.append('error="insufficient_scope"')
    scope_str = " ".join(required_list)
    if scope_str:
        parts.append(f'scope="{scope_str}"')
    if error_description:
        validated_desc = _validate_rfc6750_quoted_value(error_description)
        parts.append(f'error_description="{validated_desc}"')
    return "Bearer " + ", ".join(parts)
