"""Tests for cross-tool requirement resolution via Arcade Cloud."""

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_core.catalog import MaterializedTool, ToolCatalog, ToolMeta, create_func_models
from arcade_core.schema import (
    OAuth2Requirement,
    ToolAuthRequirement,
    ToolDefinition,
    ToolInput,
    ToolkitDefinition,
    ToolOutput,
    ToolRequirements,
    ToolSecretRequirement,
)
from arcade_mcp_server import tool
from arcade_mcp_server.convert import _build_arcade_meta
from arcade_mcp_server.server import MCPServer
from arcade_mcp_server.settings import MCPSettings


def _make_remote_tool_response(
    provider_id: str | None = None,
    provider_type: str = "oauth2",
    scopes: list[str] | None = None,
    secrets: list[dict[str, str]] | None = None,
) -> MagicMock:
    """Build a mock arcadepy ToolDefinition response."""
    mock = MagicMock()

    # Build requirements
    if provider_id or scopes or secrets:
        mock.requirements = MagicMock()

        if provider_id or scopes:
            mock.requirements.authorization = MagicMock()
            mock.requirements.authorization.provider_id = provider_id
            mock.requirements.authorization.provider_type = provider_type
            if scopes:
                mock.requirements.authorization.oauth2 = MagicMock()
                mock.requirements.authorization.oauth2.scopes = scopes
            else:
                mock.requirements.authorization.oauth2 = None
        else:
            mock.requirements.authorization = None

        if secrets:
            mock_secrets = []
            for s in secrets:
                ms = MagicMock()
                ms.key = s["key"]
                mock_secrets.append(ms)
            mock.requirements.secrets = mock_secrets
        else:
            mock.requirements.secrets = None
    else:
        mock.requirements = None

    return mock


def _make_tool_def(
    name: str = "CompoundTool",
    toolkit: str = "MyServer",
    auth: ToolAuthRequirement | None = None,
    secrets: list[ToolSecretRequirement] | None = None,
    requires_secrets_from: list[str] | None = None,
    request_scopes_from: list[str] | None = None,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        fully_qualified_name=f"{toolkit}.{name}",
        description="A compound tool",
        toolkit=ToolkitDefinition(name=toolkit, version="1.0.0"),
        input=ToolInput(parameters=[]),
        output=ToolOutput(description="output"),
        requirements=ToolRequirements(authorization=auth, secrets=secrets),
        requires_secrets_from=requires_secrets_from,
        request_scopes_from=request_scopes_from,
    )


def _make_materialized(defn: ToolDefinition) -> MaterializedTool:
    @tool
    def dummy_func() -> str:
        """A dummy function."""
        return "ok"

    input_model, output_model = create_func_models(dummy_func)
    return MaterializedTool(
        tool=dummy_func,
        definition=defn,
        meta=ToolMeta(module="test", toolkit=defn.toolkit.name),
        input_model=input_model,
        output_model=output_model,
    )


def _make_catalog(*tool_defs: ToolDefinition) -> ToolCatalog:
    catalog = ToolCatalog()
    for defn in tool_defs:
        mat = _make_materialized(defn)
        catalog._tools[defn.get_fully_qualified_name()] = mat
    return catalog


def _make_server(catalog: ToolCatalog) -> MCPServer:
    settings = MCPSettings()
    return MCPServer(
        catalog=catalog,
        name="TestServer",
        version="1.0.0",
        settings=settings,
    )


# ---------------------------------------------------------------------------
# Secret merging tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_secrets_merged_from_remote_tool() -> None:
    """Secrets from a remote tool are merged into the local tool."""
    defn = _make_tool_def(requires_secrets_from=["Gmail.ListEmails"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote_response = _make_remote_tool_response(
        secrets=[{"key": "GMAIL_API_KEY"}, {"key": "GMAIL_SECRET"}]
    )
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote_response)

    await server._resolve_cross_tool_requirements()

    secrets = defn.requirements.secrets
    assert secrets is not None
    assert {s.key for s in secrets} == {"GMAIL_API_KEY", "GMAIL_SECRET"}


@pytest.mark.asyncio
async def test_secrets_deduplicated_case_insensitive() -> None:
    """Duplicate secrets (case-insensitive) are not added twice."""
    defn = _make_tool_def(
        secrets=[ToolSecretRequirement(key="API_KEY")],
        requires_secrets_from=["Remote.Tool"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote_response = _make_remote_tool_response(secrets=[{"key": "api_key"}])
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote_response)

    await server._resolve_cross_tool_requirements()

    assert len(defn.requirements.secrets) == 1  # type: ignore[arg-type]
    assert defn.requirements.secrets[0].key == "API_KEY"  # type: ignore[index]


# ---------------------------------------------------------------------------
# Single-provider scope merging tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scopes_merged_matching_provider() -> None:
    """Scopes from a remote tool with matching provider_id are merged."""
    defn = _make_tool_def(
        auth=ToolAuthRequirement(
            provider_id="google",
            provider_type="oauth2",
            oauth2=OAuth2Requirement(scopes=["gmail.readonly"]),
        ),
        request_scopes_from=["Gmail.SendEmail"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote_response = _make_remote_tool_response(
        provider_id="google",
        scopes=["gmail.send", "gmail.readonly"],
    )
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote_response)

    await server._resolve_cross_tool_requirements()

    scopes = defn.requirements.authorization.oauth2.scopes  # type: ignore[union-attr]
    assert set(scopes) == {"gmail.readonly", "gmail.send"}
    # Single provider — resolved_authorizations should be None
    assert defn.resolved_authorizations is None


@pytest.mark.asyncio
async def test_auth_adopted_from_remote_when_local_has_none() -> None:
    """When local tool has no auth, adopt the remote tool's auth provider."""
    defn = _make_tool_def(request_scopes_from=["Gmail.ListEmails"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote_response = _make_remote_tool_response(
        provider_id="google",
        provider_type="oauth2",
        scopes=["gmail.readonly"],
    )
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote_response)

    await server._resolve_cross_tool_requirements()

    auth = defn.requirements.authorization
    assert auth is not None
    assert auth.provider_id == "google"
    assert auth.provider_type == "oauth2"
    assert auth.oauth2 is not None
    assert auth.oauth2.scopes == ["gmail.readonly"]
    # Single provider — no resolved_authorizations
    assert defn.resolved_authorizations is None


@pytest.mark.asyncio
async def test_scopes_deduplicated() -> None:
    """Duplicate scopes from remote tools are not added twice."""
    defn = _make_tool_def(
        auth=ToolAuthRequirement(
            provider_id="google",
            provider_type="oauth2",
            oauth2=OAuth2Requirement(scopes=["gmail.readonly"]),
        ),
        request_scopes_from=["Gmail.ListEmails"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote_response = _make_remote_tool_response(
        provider_id="google",
        scopes=["gmail.readonly", "gmail.send"],
    )
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote_response)

    await server._resolve_cross_tool_requirements()

    scopes = defn.requirements.authorization.oauth2.scopes  # type: ignore[union-attr]
    assert scopes == ["gmail.readonly", "gmail.send"]
    assert len(scopes) == 2  # no duplicates


# ---------------------------------------------------------------------------
# Multi-provider auth tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_provider_populates_resolved_authorizations() -> None:
    """When tools reference different providers, resolved_authorizations is populated."""
    defn = _make_tool_def(
        request_scopes_from=["Gmail.ListEmails", "Slack.SendMessage"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    gmail_response = _make_remote_tool_response(provider_id="google", scopes=["gmail.readonly"])
    slack_response = _make_remote_tool_response(provider_id="slack", scopes=["chat:write"])

    async def mock_get(name: str) -> MagicMock:
        if "Gmail" in name:
            return gmail_response
        return slack_response

    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(side_effect=mock_get)

    await server._resolve_cross_tool_requirements()

    # resolved_authorizations should have both providers
    assert defn.resolved_authorizations is not None
    assert len(defn.resolved_authorizations) == 2
    provider_ids = {a.provider_id for a in defn.resolved_authorizations}
    assert provider_ids == {"google", "slack"}

    # authorization (singular) should be set to first provider for backward compat
    assert defn.requirements.authorization is not None
    assert defn.requirements.authorization.provider_id == "google"


@pytest.mark.asyncio
async def test_multi_provider_with_existing_local_auth() -> None:
    """Local tool with Google auth + remote Slack → resolved_authorizations has both."""
    defn = _make_tool_def(
        auth=ToolAuthRequirement(
            provider_id="google",
            provider_type="oauth2",
            oauth2=OAuth2Requirement(scopes=["gmail.readonly"]),
        ),
        request_scopes_from=["Slack.SendMessage"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    slack_response = _make_remote_tool_response(provider_id="slack", scopes=["chat:write"])
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=slack_response)

    await server._resolve_cross_tool_requirements()

    # Multi-provider: resolved_authorizations has both
    assert defn.resolved_authorizations is not None
    assert len(defn.resolved_authorizations) == 2

    google_auth = next(a for a in defn.resolved_authorizations if a.provider_id == "google")
    slack_auth = next(a for a in defn.resolved_authorizations if a.provider_id == "slack")

    assert google_auth.oauth2 is not None
    assert "gmail.readonly" in (google_auth.oauth2.scopes or [])
    assert slack_auth.oauth2 is not None
    assert "chat:write" in (slack_auth.oauth2.scopes or [])


@pytest.mark.asyncio
async def test_multi_provider_merges_same_provider_scopes() -> None:
    """Multiple remote tools with the same provider have their scopes merged."""
    defn = _make_tool_def(
        request_scopes_from=["Gmail.ListEmails", "Gmail.SendEmail", "Slack.SendMessage"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    gmail_list_response = _make_remote_tool_response(
        provider_id="google", scopes=["gmail.readonly"]
    )
    gmail_send_response = _make_remote_tool_response(provider_id="google", scopes=["gmail.send"])
    slack_response = _make_remote_tool_response(provider_id="slack", scopes=["chat:write"])

    async def mock_get(name: str) -> MagicMock:
        if "ListEmails" in name:
            return gmail_list_response
        if "SendEmail" in name:
            return gmail_send_response
        return slack_response

    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(side_effect=mock_get)

    await server._resolve_cross_tool_requirements()

    assert defn.resolved_authorizations is not None
    assert len(defn.resolved_authorizations) == 2  # google + slack, not 3

    google_auth = next(a for a in defn.resolved_authorizations if a.provider_id == "google")
    assert google_auth.oauth2 is not None
    assert set(google_auth.oauth2.scopes or []) == {"gmail.readonly", "gmail.send"}


# ---------------------------------------------------------------------------
# MCP metadata conversion tests
# ---------------------------------------------------------------------------


class TestBuildArcadeMeta:
    def test_multi_provider_emits_authorizations_list(self) -> None:
        """_build_arcade_meta includes authorizations (plural) for multi-provider tools."""
        defn = _make_tool_def(
            auth=ToolAuthRequirement(
                provider_id="google",
                provider_type="oauth2",
                oauth2=OAuth2Requirement(scopes=["gmail.readonly"]),
            ),
        )
        defn.resolved_authorizations = [
            ToolAuthRequirement(
                provider_id="google",
                provider_type="oauth2",
                oauth2=OAuth2Requirement(scopes=["gmail.readonly"]),
            ),
            ToolAuthRequirement(
                provider_id="slack",
                provider_type="oauth2",
                oauth2=OAuth2Requirement(scopes=["chat:write"]),
            ),
        ]

        meta = _build_arcade_meta(defn)

        assert meta is not None
        assert "requirements" in meta
        assert "authorizations" in meta["requirements"]
        auths = meta["requirements"]["authorizations"]
        assert len(auths) == 2
        provider_ids = {a["provider_id"] for a in auths}
        assert provider_ids == {"google", "slack"}

    def test_single_provider_no_authorizations_key(self) -> None:
        """Single-provider tools should NOT have an authorizations (plural) key."""
        defn = _make_tool_def(
            auth=ToolAuthRequirement(
                provider_id="google",
                provider_type="oauth2",
                oauth2=OAuth2Requirement(scopes=["gmail.readonly"]),
            ),
        )

        meta = _build_arcade_meta(defn)

        assert meta is not None
        assert "requirements" in meta
        assert "authorizations" not in meta["requirements"]

    def test_no_auth_no_requirements(self) -> None:
        """Tool with no auth/secrets/metadata has no requirements in meta."""
        defn = _make_tool_def()

        meta = _build_arcade_meta(defn)

        assert meta is None


# ---------------------------------------------------------------------------
# MaterializedTool.requires_auth tests
# ---------------------------------------------------------------------------


class TestRequiresAuth:
    def test_requires_auth_with_resolved_authorizations(self) -> None:
        """requires_auth is True when resolved_authorizations is set."""
        defn = _make_tool_def()
        defn.resolved_authorizations = [
            ToolAuthRequirement(provider_id="google", provider_type="oauth2"),
        ]
        mat = _make_materialized(defn)
        assert mat.requires_auth is True

    def test_requires_auth_with_single_authorization(self) -> None:
        """requires_auth is True when single authorization is set."""
        defn = _make_tool_def(
            auth=ToolAuthRequirement(provider_id="google", provider_type="oauth2"),
        )
        mat = _make_materialized(defn)
        assert mat.requires_auth is True

    def test_requires_auth_false_when_no_auth(self) -> None:
        """requires_auth is False when no auth is set."""
        defn = _make_tool_def()
        mat = _make_materialized(defn)
        assert mat.requires_auth is False


# ---------------------------------------------------------------------------
# Error handling and edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remote_tool_not_found_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """If remote tool fetch fails, a warning is logged and resolution continues."""
    defn = _make_tool_def(requires_secrets_from=["NonExistent.Tool"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(side_effect=Exception("Not found"))

    with caplog.at_level(logging.WARNING):
        await server._resolve_cross_tool_requirements()

    assert "Failed to fetch remote tool" in caplog.text
    assert defn.requirements.secrets is None  # unchanged


@pytest.mark.asyncio
async def test_no_arcade_client_skips_resolution(caplog: pytest.LogCaptureFixture) -> None:
    """When Arcade client is None and tools need resolution, a warning is logged."""
    defn = _make_tool_def(request_scopes_from=["Gmail.ListEmails"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)
    server.arcade = None

    with caplog.at_level(logging.WARNING):
        await server._resolve_cross_tool_requirements()

    assert "no Arcade client is configured" in caplog.text


@pytest.mark.asyncio
async def test_no_references_is_noop() -> None:
    """Tools without cross-tool references are not modified."""
    defn = _make_tool_def()
    catalog = _make_catalog(defn)
    server = _make_server(catalog)
    server.arcade = AsyncMock()

    await server._resolve_cross_tool_requirements()

    # arcade.tools.get should never be called
    server.arcade.tools.get.assert_not_called()
    assert defn.requirements.authorization is None
    assert defn.requirements.secrets is None


@pytest.mark.asyncio
async def test_remote_tool_with_no_requirements_skipped() -> None:
    """A remote tool that has no requirements is silently skipped."""
    defn = _make_tool_def(requires_secrets_from=["Empty.Tool"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote_response = _make_remote_tool_response()  # no requirements
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote_response)

    await server._resolve_cross_tool_requirements()

    assert defn.requirements.secrets is None


@pytest.mark.asyncio
async def test_multiple_remote_tools_secrets_and_scopes() -> None:
    """Multiple remote tools have both secrets and scopes merged correctly."""
    defn = _make_tool_def(
        requires_secrets_from=["Gmail.ListEmails", "Slack.SendMessage"],
        request_scopes_from=["Gmail.ListEmails"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    gmail_response = _make_remote_tool_response(
        provider_id="google",
        scopes=["gmail.readonly"],
        secrets=[{"key": "GMAIL_TOKEN"}],
    )
    slack_response = _make_remote_tool_response(
        provider_id="slack",
        scopes=["chat:write"],
        secrets=[{"key": "SLACK_TOKEN"}],
    )

    async def mock_get(name: str) -> MagicMock:
        if "Gmail" in name:
            return gmail_response
        return slack_response

    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(side_effect=mock_get)

    await server._resolve_cross_tool_requirements()

    # Secrets from both tools merged
    secret_keys = {s.key for s in defn.requirements.secrets}  # type: ignore[union-attr]
    assert secret_keys == {"GMAIL_TOKEN", "SLACK_TOKEN"}

    # Auth adopted from Gmail (single provider in request_scopes_from)
    auth = defn.requirements.authorization
    assert auth is not None
    assert auth.provider_id == "google"
    # Only one provider referenced via scopes — no resolved_authorizations
    assert defn.resolved_authorizations is None


# ---------------------------------------------------------------------------
# Edge cases for cross-tool requirement resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_remote_tool_with_requirements_but_no_secrets() -> None:
    """Remote tool has requirements object but secrets is empty → skipped."""
    defn = _make_tool_def(requires_secrets_from=["Tool.NoSecrets"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    # Build a remote response with requirements but no secrets
    remote = MagicMock()
    remote.requirements = MagicMock()
    remote.requirements.secrets = None
    remote.requirements.authorization = None

    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote)

    await server._resolve_cross_tool_requirements()
    assert defn.requirements.secrets is None


@pytest.mark.asyncio
async def test_scopes_remote_not_found_skipped() -> None:
    """When a request_scopes_from reference fails to fetch, it's skipped."""
    defn = _make_tool_def(request_scopes_from=["Missing.Tool"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(side_effect=Exception("Not found"))

    await server._resolve_cross_tool_requirements()
    assert defn.requirements.authorization is None


@pytest.mark.asyncio
async def test_scopes_remote_has_no_requirements() -> None:
    """Remote tool fetched for scopes but has no requirements → skipped."""
    defn = _make_tool_def(request_scopes_from=["Empty.Tool"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote = MagicMock()
    remote.requirements = None
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote)

    await server._resolve_cross_tool_requirements()
    assert defn.requirements.authorization is None


@pytest.mark.asyncio
async def test_scopes_remote_has_no_auth() -> None:
    """Remote tool has requirements but no authorization → skipped for scopes."""
    defn = _make_tool_def(request_scopes_from=["Tool.NoAuth"])
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote = MagicMock()
    remote.requirements = MagicMock()
    remote.requirements.authorization = None
    remote.requirements.secrets = None
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote)

    await server._resolve_cross_tool_requirements()
    assert defn.requirements.authorization is None


@pytest.mark.asyncio
async def test_same_provider_merge_with_null_oauth2() -> None:
    """When same-provider merge encounters existing entry with oauth2=None."""
    defn = _make_tool_def(
        auth=ToolAuthRequirement(
            provider_id="google",
            provider_type="oauth2",
            oauth2=None,  # No oauth2 on local tool
        ),
        request_scopes_from=["Gmail.ListEmails"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote = _make_remote_tool_response(
        provider_id="google",
        scopes=["gmail.readonly"],
    )
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote)

    await server._resolve_cross_tool_requirements()

    auth = defn.requirements.authorization
    assert auth is not None
    assert auth.oauth2 is not None
    assert auth.oauth2.scopes == ["gmail.readonly"]


@pytest.mark.asyncio
async def test_same_provider_merge_with_null_scopes_list() -> None:
    """When same-provider merge encounters existing oauth2 with scopes=None."""
    defn = _make_tool_def(
        auth=ToolAuthRequirement(
            provider_id="google",
            provider_type="oauth2",
            oauth2=OAuth2Requirement(scopes=None),
        ),
        request_scopes_from=["Gmail.ListEmails"],
    )
    catalog = _make_catalog(defn)
    server = _make_server(catalog)

    remote = _make_remote_tool_response(
        provider_id="google",
        scopes=["gmail.readonly"],
    )
    server.arcade = AsyncMock()
    server.arcade.tools.get = AsyncMock(return_value=remote)

    await server._resolve_cross_tool_requirements()

    auth = defn.requirements.authorization
    assert auth is not None
    assert auth.oauth2 is not None
    assert "gmail.readonly" in auth.oauth2.scopes
