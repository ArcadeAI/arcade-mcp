import pytest

# --- Dummy Config Objects ---
# Define simple structures or use MagicMock to mimic the expected config.
# Adjust attributes based on actual usage during import/startup.


class DummyUserConfig:
    email: str | None = "test-user@example.com"


class DummyApiConfig:
    key: str | None = "dummy-api-key"
    host: str | None = "dummy-host"
    port: int | None = 1234
    tls: bool = False


class DummyCloudConfig:
    key: str | None = "dummy-cloud-key"
    host: str | None = "dummy-cloud-host"
    port: int | None = 4321
    tls: bool = False


class DummyConfig:
    user: DummyUserConfig | None = DummyUserConfig()
    api: DummyApiConfig | None = DummyApiConfig()
    cloud: DummyCloudConfig | None = DummyCloudConfig()


# --- Fixtures ---


@pytest.fixture(autouse=True)
def mock_global_config(monkeypatch):
    """
    Mocks the global configuration loading during test collection and execution
    to prevent errors related to missing/invalid credentials or config files.
    """
    dummy_config_instance = DummyConfig()

    # Mock the primary function used to get the config object
    monkeypatch.setattr("arcade.core.config.get_config", lambda: dummy_config_instance)

    # Also mock the validation function used in CLI commands, as it might also load config
    monkeypatch.setattr("arcade.cli.utils.validate_and_get_config", lambda: dummy_config_instance)
