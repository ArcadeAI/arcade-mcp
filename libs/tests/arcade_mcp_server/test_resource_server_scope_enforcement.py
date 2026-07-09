"""Tests for ``arcade_mcp_server.resource_server.scope_enforcement.enforce_scopes``."""

import pytest
from arcade_mcp_server.resource_server import (
    InsufficientScopeError,
    ResourceOwner,
    enforce_scopes,
)
from arcade_mcp_server.resource_server.middleware import RESOURCE_OWNER_SCOPE_KEY


class TestEnforceScopes:
    """Behavior tests for the public ``enforce_scopes`` helper."""

    def test_resource_owner_scope_key_constant(self):
        """The constant is part of the contract: middleware writes to it,
        ``enforce_scopes`` reads from it. A rename must be deliberate.
        """
        assert RESOURCE_OWNER_SCOPE_KEY == "resource_owner"

    def test_passes_when_all_required_granted(self):
        owner = ResourceOwner(
            user_id="u", granted_scopes=frozenset({"read", "write"})
        )
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        # Should not raise
        enforce_scopes(scope, ["read"])

    def test_raises_insufficient_scope_when_missing(self):
        owner = ResourceOwner(user_id="u", granted_scopes=frozenset({"read"}))
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        with pytest.raises(InsufficientScopeError) as exc_info:
            enforce_scopes(scope, ["read", "write"])
        # Pin "minimum approach": required is the FULL caller list, not
        # just the missing subset.
        assert exc_info.value.required_scopes == ("read", "write")
        assert exc_info.value.granted_scopes == frozenset({"read"})

    def test_passes_required_in_full_not_missing_only(self):
        """Pin against the missing-only regression: ``required_scopes`` on
        the raised exception is the WHOLE input list, not the missing
        subset. The header builder needs the full operation requirement
        to advertise the right step-up scope set.
        """
        owner = ResourceOwner(user_id="u", granted_scopes=frozenset({"read"}))
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        with pytest.raises(InsufficientScopeError) as exc_info:
            enforce_scopes(scope, ["read", "write"])
        assert exc_info.value.required_scopes == ("read", "write")
        # NOT just ("write",)
        assert "read" in exc_info.value.required_scopes

    def test_with_no_resource_owner_in_scope_raises_runtime_error(self):
        with pytest.raises(RuntimeError, match="ResourceServerMiddleware"):
            enforce_scopes({}, ["read"])

    def test_handles_iterable_required(self):
        """Generator-exhaustion footgun: if ``required`` is consumed twice,
        the order-preserving rebuild fails. The implementation must
        materialize once.
        """

        def gen():
            yield "read"
            yield "write"

        owner = ResourceOwner(
            user_id="u", granted_scopes=frozenset({"read", "write"})
        )
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        # Should not raise: granted has both scopes.
        enforce_scopes(scope, gen())

    def test_with_empty_required_does_not_raise(self):
        owner = ResourceOwner(user_id="u", granted_scopes=frozenset())
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        # Vacuous: no required scopes means no enforcement.
        enforce_scopes(scope, [])

    def test_does_not_mutate_scope_dict(self):
        owner = ResourceOwner(user_id="u", granted_scopes=frozenset({"read"}))
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        before = dict(scope)
        enforce_scopes(scope, ["read"])
        assert scope == before

    def test_preserves_caller_order_in_required_when_raising(self):
        owner = ResourceOwner(user_id="u", granted_scopes=frozenset())
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        with pytest.raises(InsufficientScopeError) as exc_info:
            enforce_scopes(scope, ["c", "a", "b"])
        assert exc_info.value.required_scopes == ("c", "a", "b")

    def test_does_not_crash_when_granted_has_malformed_token(self):
        """Pin: a non-RFC-conformant token in ``ResourceOwner.granted_scopes``
        (e.g., from a custom validator that does not filter, or direct
        fixture construction) MUST NOT prevent ``enforce_scopes`` from
        raising ``InsufficientScopeError``. Validating the granted set at
        exception construction would convert this into an unhandled
        ``ValueError`` that the middleware's
        ``except InsufficientScopeError`` handler cannot catch, collapsing
        the 403 step-up flow into a 500.
        """
        owner = ResourceOwner(
            user_id="u",
            granted_scopes=frozenset({"bad token", "files:read"}),
        )
        scope = {RESOURCE_OWNER_SCOPE_KEY: owner}
        with pytest.raises(InsufficientScopeError) as exc_info:
            enforce_scopes(scope, ["files:write"])
        assert exc_info.value.required_scopes == ("files:write",)
        assert exc_info.value.granted_scopes == frozenset(
            {"bad token", "files:read"}
        )


class TestBuildInsufficientScopeWWWAuthenticate:
    """Tests for the shared ``build_insufficient_scope_www_authenticate``
    helper used by both the middleware and the ``MCPServer`` inline
    JSON-RPC 403 path.
    """

    def _build(self, **kwargs):
        from arcade_mcp_server.resource_server import (
            build_insufficient_scope_www_authenticate,
        )

        return build_insufficient_scope_www_authenticate(**kwargs)

    def test_accepts_well_formed_inputs(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url="https://mcp.example.com/.well-known/oauth-protected-resource/mcp",
            error_description="needs read",
        )
        assert result.startswith("Bearer ")
        assert 'error="insufficient_scope"' in result
        assert 'scope="read"' in result
        assert (
            'resource_metadata="https://mcp.example.com/.well-known/oauth-protected-resource/mcp"'
            in result
        )
        assert 'error_description="needs read"' in result

    def test_rejects_malformed_scope_token(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["bad token"],
                resource_metadata_url=None,
            )

    def test_rejects_scope_token_with_dquote(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=['has"quote'],
                resource_metadata_url=None,
            )

    def test_rejects_scope_token_with_backslash(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=[r"path\to"],
                resource_metadata_url=None,
            )

    def test_rejects_resource_metadata_url_with_dquote(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url='https://example.com/"injection"',
            )

    def test_rejects_resource_metadata_url_with_crlf(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="https://example.com/\r\nX-Injected: 1",
            )

    def test_rejects_resource_metadata_url_with_space(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="hello world",
            )

    def test_rejects_resource_metadata_url_without_scheme(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="example.com/mcp",
            )

    def test_rejects_resource_metadata_url_with_non_http_scheme(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="ftp://example.com/mcp",
            )

    def test_rejects_resource_metadata_url_with_empty_netloc(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="https:///path",
            )

    def test_rejects_resource_metadata_url_http_for_non_loopback_host(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url=(
                    "http://api.example.com/.well-known/oauth-protected-resource/mcp"
                ),
            )

    def test_rejects_resource_metadata_url_http_for_0_0_0_0(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="http://0.0.0.0:8000/mcp",
            )

    def test_rejects_resource_metadata_url_http_for_private_ip(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="http://192.168.1.50:8000/mcp",
            )

    def test_rejects_resource_metadata_url_with_unencoded_whitespace_in_host(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url=(
                    "https://exa mple.com/.well-known/oauth-protected-resource/mcp"
                ),
            )

    def test_rejects_resource_metadata_url_with_unencoded_whitespace_in_path(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url=(
                    "https://mcp.example.com/.well-known/oauth-protected-resource/a b"
                ),
            )

    def test_rejects_resource_metadata_url_with_malformed_percent_escape(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="https://mcp.example.com/%zz",
            )

    def test_rejects_resource_metadata_url_with_truncated_percent_escape(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="https://mcp.example.com/path%2",
            )

    def test_accepts_resource_metadata_url_with_well_formed_percent_escape(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url="https://mcp.example.com/space%20path",
        )
        assert "https://mcp.example.com/space%20path" in result

    def test_rejects_resource_metadata_url_with_fragment(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url="https://mcp.example.com#fragment",
            )

    def test_rejects_resource_metadata_url_with_bare_hash(self):
        with pytest.raises(ValueError):
            self._build(
                required_scopes=["read"],
                resource_metadata_url=(
                    "https://mcp.example.com/.well-known/oauth-protected-resource/mcp#"
                ),
            )

    def test_accepts_resource_metadata_url_with_query(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url=(
                "https://mcp.example.com/.well-known/oauth-protected-resource/mcp?tenant=acme"
            ),
        )
        assert "?tenant=acme" in result

    def test_accepts_https_resource_metadata_url(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url=(
                "https://mcp.example.com/.well-known/oauth-protected-resource/mcp"
            ),
        )
        assert "https://mcp.example.com" in result

    def test_accepts_http_resource_metadata_url_for_127_0_0_1(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url=(
                "http://127.0.0.1:8000/.well-known/oauth-protected-resource/mcp"
            ),
        )
        assert "http://127.0.0.1" in result

    def test_accepts_http_resource_metadata_url_for_localhost(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url=(
                "http://localhost:8000/.well-known/oauth-protected-resource/mcp"
            ),
        )
        assert "http://localhost" in result

    def test_accepts_http_resource_metadata_url_for_ipv6_loopback(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url=(
                "http://[::1]:8000/.well-known/oauth-protected-resource/mcp"
            ),
        )
        assert "[::1]" in result

    def test_omits_scope_param_when_required_empty(self):
        result = self._build(
            required_scopes=[],
            resource_metadata_url=None,
        )
        assert "scope=" not in result

    def test_omits_resource_metadata_when_url_none(self):
        result = self._build(
            required_scopes=["read"],
            resource_metadata_url=None,
        )
        assert "resource_metadata=" not in result
