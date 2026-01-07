"""Tests for MCP Settings."""

from arcade_mcp_server.settings import MCPSettings, ServerSettings


class TestServerSettings:
    """Test ServerSettings class."""

    def test_server_settings_defaults(self):
        """Test ServerSettings default values."""
        settings = ServerSettings()

        assert settings.name == "ArcadeMCP"
        assert settings.version == "0.1.0dev"
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
        assert settings.server.version == "0.1.0dev"
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
