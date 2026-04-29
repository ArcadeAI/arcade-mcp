"""Tests for MCP Settings."""

import pytest
from pydantic import ValidationError

from arcade_mcp_server.settings import ArcadeSettings, MCPSettings, ServerSettings


class TestServerSettings:
    """Test ServerSettings class."""

    def test_server_settings_defaults(self):
        """Test ServerSettings default values."""
        settings = ServerSettings()

        assert settings.name == "ArcadeMCP"
        assert settings.version == "0.1.0"
        assert settings.title == "ArcadeMCP"
        assert settings.instructions is not None
        assert "available tools" in settings.instructions.lower()

    def test_server_settings_custom_values(self):
        """Test ServerSettings with custom values."""
        settings = ServerSettings(
            name="CustomServer",
            version="2.0.0",
            title="Custom Title",
            instructions="Custom instructions",
        )

        assert settings.name == "CustomServer"
        assert settings.version == "2.0.0"
        assert settings.title == "Custom Title"
        assert settings.instructions == "Custom instructions"

    def test_server_settings_partial_values(self):
        """Test ServerSettings with partial custom values."""
        settings = ServerSettings(
            name="PartialServer",
            version="1.5.0",
        )

        assert settings.name == "PartialServer"
        assert settings.version == "1.5.0"
        assert settings.title == "ArcadeMCP"  # Default value
        assert settings.instructions is not None  # Default value


class TestMCPSettings:
    """Test MCPSettings class."""

    def test_mcp_settings_defaults(self):
        """Test MCPSettings default values."""
        settings = MCPSettings()

        assert settings.server.name == "ArcadeMCP"
        assert settings.server.version == "0.1.0"
        assert settings.server.title == "ArcadeMCP"
        assert settings.server.instructions is not None

    def test_mcp_settings_with_custom_server(self):
        """Test MCPSettings with custom ServerSettings."""
        server_settings = ServerSettings(
            name="TestServer",
            version="3.0.0",
            title="Test Title",
            instructions="Test instructions",
        )
        settings = MCPSettings(server=server_settings)

        assert settings.server.name == "TestServer"
        assert settings.server.version == "3.0.0"
        assert settings.server.title == "Test Title"
        assert settings.server.instructions == "Test instructions"

    def test_mcp_settings_from_env(self, monkeypatch):
        """Test MCPSettings.from_env() uses environment variables."""
        monkeypatch.setenv("MCP_SERVER_NAME", "EnvServer")
        monkeypatch.setenv("MCP_SERVER_VERSION", "4.0.0")
        monkeypatch.setenv("MCP_SERVER_TITLE", "Env Title")
        monkeypatch.setenv("MCP_SERVER_INSTRUCTIONS", "Env instructions")

        settings = MCPSettings.from_env()

        assert settings.server.name == "EnvServer"
        assert settings.server.version == "4.0.0"
        assert settings.server.title == "Env Title"
        assert settings.server.instructions == "Env instructions"


class TestServerSettingsTitleDefault:
    """Test that the default title value is 'ArcadeMCP'."""

    def test_title_default_value(self):
        """Test that the default title value is 'ArcadeMCP'."""
        settings = ServerSettings()
        assert settings.title == "ArcadeMCP"

    def test_title_field_default(self):
        """Test that the title field default is 'ArcadeMCP'."""
        field_info = ServerSettings.model_fields["title"]
        assert field_info.default == "ArcadeMCP"


class TestServerSettingsVersionValidation:
    """Tests for ServerSettings version validation (semver enforcement)."""

    def test_server_settings_rejects_invalid_version(self) -> None:
        """Test ServerSettings raises ValidationError for invalid version."""
        with pytest.raises(ValidationError, match="semver"):
            ServerSettings(version="bad")

    def test_server_settings_accepts_valid_semver(self) -> None:
        """Test ServerSettings accepts valid semver."""
        settings = ServerSettings(version="1.2.3-alpha.1+build.456")
        assert settings.version == "1.2.3-alpha.1+build.456"

    def test_server_settings_normalizes_short_version(self) -> None:
        """Test ServerSettings normalizes MAJOR.MINOR to MAJOR.MINOR.0."""
        settings = ServerSettings(version="1.0")
        assert settings.version == "1.0.0"

    def test_server_settings_normalizes_v_prefix(self) -> None:
        """Test ServerSettings strips v prefix and normalizes the version."""
        settings = ServerSettings(version="v1.0.0")
        assert settings.version == "1.0.0"

    def test_server_settings_normalizes_v_prefix_short(self) -> None:
        """Test ServerSettings strips v prefix from short versions."""
        settings = ServerSettings(version="v1.0")
        assert settings.version == "1.0.0"

    def test_server_settings_normalizes_major_only(self) -> None:
        """Test ServerSettings normalizes MAJOR to MAJOR.0.0."""
        settings = ServerSettings(version="1")
        assert settings.version == "1.0.0"

    def test_server_settings_normalizes_v_major_only(self) -> None:
        """Test ServerSettings strips v prefix from major-only versions."""
        settings = ServerSettings(version="v1")
        assert settings.version == "1.0.0"

    def test_mcp_settings_env_rejects_invalid_version(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test MCP_SERVER_VERSION env var is validated."""
        monkeypatch.setenv("MCP_SERVER_VERSION", "not-valid")
        with pytest.raises(ValidationError, match="semver"):
            MCPSettings.from_env()


class TestArcadeSettingsCoordinatorUrl:
    """Tests for the new ArcadeSettings.coordinator_url field."""

    def test_arcade_settings_coordinator_url_default(self) -> None:
        """Default coordinator URL is the public Arcade Cloud URL."""
        settings = ArcadeSettings()
        assert settings.coordinator_url == "https://cloud.arcade.dev"

    def test_arcade_settings_reads_coordinator_url_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ARCADE_COORDINATOR_URL env var overrides the default."""
        monkeypatch.setenv("ARCADE_COORDINATOR_URL", "https://staging.arcade.dev")
        settings = ArcadeSettings()
        assert settings.coordinator_url == "https://staging.arcade.dev"
