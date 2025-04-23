import pytest


class TestUserConfig:
    email: str | None = "test-user@example.com"


class TestApiConfig:
    key: str | None = "test-api-key"
    host: str | None = "test-host"
    port: int | None = 1234
    tls: bool = False


class TestCloudConfig:
    key: str | None = "test-cloud-key"
    host: str | None = "test-cloud-host"
    port: int | None = 4321
    tls: bool = False


class TestConfig:
    user: TestUserConfig | None = TestUserConfig()
    api: TestApiConfig | None = TestApiConfig()
    cloud: TestCloudConfig | None = TestCloudConfig()


# --- Fixtures ---


@pytest.fixture(autouse=True)
def mock_global_config(monkeypatch):
    """
    Mocks the global configuration loading during test collection and execution
    to prevent errors related to missing/invalid credentials or config files.
    """
    test_config_instance = TestConfig()

    # Mock the primary function used to get the config object
    monkeypatch.setattr("arcade.core.config.get_config", lambda: test_config_instance)

    # Also mock the validation function used in CLI commands, as it might also load config
    monkeypatch.setattr("arcade.cli.utils.validate_and_get_config", lambda: test_config_instance)
