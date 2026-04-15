"""Tests for MCP protocol version negotiation."""

from arcade_mcp_server.types import (
    LATEST_PROTOCOL_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    VERSION_FEATURES,
    negotiate_version,
    version_has_feature,
)


class TestNegotiateVersion:
    """Tests for the negotiate_version() function.

    Spec rule: if server supports the requested version, return it.
    Otherwise, return latest supported version (NOT latest <= client).
    Client decides whether to disconnect if it doesn't support the response.
    """

    def test_client_sends_exact_supported_version_2025_06_18(self) -> None:
        assert negotiate_version("2025-06-18") == "2025-06-18"

    def test_client_sends_exact_supported_version_2025_11_25(self) -> None:
        assert negotiate_version("2025-11-25") == "2025-11-25"

    def test_client_sends_future_version_gets_latest(self) -> None:
        """Unsupported version -> server returns its latest supported."""
        assert negotiate_version("2030-01-01") == "2025-11-25"

    def test_client_sends_ancient_version_gets_latest(self) -> None:
        """Unsupported version -> server returns its latest, even if newer than client's.
        Client will disconnect if it can't handle this version."""
        assert negotiate_version("2020-01-01") == "2025-11-25"

    def test_client_sends_version_between_supported_gets_latest(self) -> None:
        """2025-09-01 is not an exact match -> server returns latest (2025-11-25).
        NOT 2025-06-18, because spec says 'latest supported', not 'latest <= client'."""
        assert negotiate_version("2025-09-01") == "2025-11-25"

    def test_supported_versions_match_declared_precedence(self) -> None:
        """Versions are listed in explicit precedence order (oldest first, latest last).
        Do NOT use sorted() -- lexical ordering breaks for non-date identifiers
        like DRAFT-2025-v3 that already appear in spec artifacts (schema.ts:14)."""
        assert SUPPORTED_PROTOCOL_VERSIONS == ["2025-06-18", "2025-11-25"]

    def test_latest_is_last_supported(self) -> None:
        assert LATEST_PROTOCOL_VERSION == SUPPORTED_PROTOCOL_VERSIONS[-1]

    def test_no_duplicate_versions(self) -> None:
        assert len(SUPPORTED_PROTOCOL_VERSIONS) == len(set(SUPPORTED_PROTOCOL_VERSIONS))


class TestVersionHasFeature:
    """Tests for version_has_feature() and VERSION_FEATURES registry."""

    def test_base_present_in_all_versions(self) -> None:
        for version in SUPPORTED_PROTOCOL_VERSIONS:
            assert version_has_feature(version, "base") is True

    def test_tasks_only_in_2025_11_25(self) -> None:
        assert version_has_feature("2025-06-18", "tasks") is False
        assert version_has_feature("2025-11-25", "tasks") is True

    def test_tool_execution_only_in_2025_11_25(self) -> None:
        assert version_has_feature("2025-06-18", "tool_execution") is False
        assert version_has_feature("2025-11-25", "tool_execution") is True

    def test_unknown_version_returns_false(self) -> None:
        assert version_has_feature("9999-01-01", "base") is False

    def test_unknown_feature_returns_false(self) -> None:
        assert version_has_feature("2025-11-25", "nonexistent_feature") is False

    def test_2025_06_18_features_are_subset_of_2025_11_25(self) -> None:
        """All features in 2025-06-18 must also be present in 2025-11-25."""
        assert VERSION_FEATURES["2025-06-18"].issubset(VERSION_FEATURES["2025-11-25"])
