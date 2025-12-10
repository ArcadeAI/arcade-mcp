import json
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from arcade_core.usage import UsageIdentity


@pytest.fixture
def temp_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Setup temporary config directory for testing."""
    config_dir = tmp_path / ".arcade"
    config_dir.mkdir()
    credentials_file = config_dir / "credentials.yaml"

    monkeypatch.setattr("arcade_core.usage.identity.ARCADE_CONFIG_PATH", str(config_dir))
    monkeypatch.setattr("arcade_core.usage.identity.CREDENTIALS_FILE_PATH", str(credentials_file))

    return config_dir


@pytest.fixture
def identity(temp_config_path: Path) -> UsageIdentity:
    """Create a UsageIdentity instance with temp config path."""
    # NOTE: Although temp_config_path is directly used, it's required to ensure that
    # this fixture depends on the temp_config_path fixture to apply the monkeypatch
    # before creating the UsageIdentity instance
    return UsageIdentity()


class TestLoadOrCreate:
    """Tests for load_or_create() method."""

    def test_creates_new_file_when_not_exists(
        self, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that load_or_create creates a new usage.json file when it doesn't exist."""
        data = identity.load_or_create()

        assert "anon_id" in data
        assert data["linked_principal_id"] is None
        assert uuid.UUID(data["anon_id"])  # Validate UUID format

        # Verify file was created
        usage_file = temp_config_path / "usage.json"
        assert usage_file.exists()

    def test_loads_existing_file(self, identity: UsageIdentity, temp_config_path: Path) -> None:
        """Test that load_or_create loads existing usage.json file."""
        existing_data = {"anon_id": str(uuid.uuid4()), "linked_principal_id": "user-123"}
        usage_file = temp_config_path / "usage.json"
        usage_file.write_text(json.dumps(existing_data))

        data = identity.load_or_create()

        assert data["anon_id"] == existing_data["anon_id"]
        assert data["linked_principal_id"] == existing_data["linked_principal_id"]

    def test_caches_data_after_first_load(self, identity: UsageIdentity) -> None:
        """Test that load_or_create caches data after first load."""
        first_data = identity.load_or_create()
        second_data = identity.load_or_create()

        # Should return the same object b/c it's cached
        assert first_data is second_data

    def test_creates_new_data_on_corrupted_json(
        self, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that load_or_create creates new data if JSON is corrupted."""
        usage_file = temp_config_path / "usage.json"
        usage_file.write_text("{ invalid json }")

        data = identity.load_or_create()

        assert "anon_id" in data
        assert data["linked_principal_id"] is None

    def test_creates_new_data_on_missing_anon_id(
        self, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that load_or_create creates new data if anon_id is missing."""
        usage_file = temp_config_path / "usage.json"
        usage_file.write_text(json.dumps({"some_other_key": "value"}))

        data = identity.load_or_create()

        assert "anon_id" in data
        assert data["linked_principal_id"] is None

    def test_creates_new_data_on_non_dict_json(
        self, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that load_or_create creates new data if JSON is not a dict."""
        usage_file = temp_config_path / "usage.json"
        usage_file.write_text(json.dumps(["not", "a", "dict"]))

        data = identity.load_or_create()

        assert "anon_id" in data
        assert isinstance(data, dict)


class TestWriteAtomic:
    """Tests for _write_atomic() method."""

    def test_writes_data_to_file(self, identity: UsageIdentity, temp_config_path: Path) -> None:
        """Test that _write_atomic writes data to usage.json."""
        test_data = {"anon_id": str(uuid.uuid4()), "linked_principal_id": "user-456"}

        identity._write_atomic(test_data)

        usage_file = temp_config_path / "usage.json"
        assert usage_file.exists()

        with usage_file.open() as f:
            loaded_data = json.load(f)

        assert loaded_data == test_data

    def test_atomic_write_cleans_up_on_failure(
        self, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that _write_atomic cleans up temp file on failure."""
        with (
            patch(
                "tempfile.mkstemp", return_value=(999, str(temp_config_path / ".usage_temp.tmp"))
            ),
            patch("os.fdopen", side_effect=Exception("Write failed")),
        ):
            with pytest.raises(Exception, match="Write failed"):
                identity._write_atomic({"anon_id": "test"})

        # Verify no temp files are left behind
        temp_files = list(temp_config_path.glob(".usage_*.tmp"))
        assert len(temp_files) == 0


class TestGetDistinctId:
    """Tests for get_distinct_id() method."""

    def test_returns_linked_principal_id_when_persisted(
        self, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that get_distinct_id returns persisted linked_principal_id."""
        usage_file = temp_config_path / "usage.json"
        usage_file.write_text(
            json.dumps({"anon_id": str(uuid.uuid4()), "linked_principal_id": "persisted-user-123"})
        )

        distinct_id = identity.get_distinct_id()

        assert distinct_id == "persisted-user-123"

    @patch("arcade_core.usage.identity.UsageIdentity.get_principal_id")
    def test_returns_principal_id_from_api_when_not_persisted(
        self, mock_get_principal: MagicMock, identity: UsageIdentity
    ) -> None:
        """Test that get_distinct_id fetches principal_id from API when not persisted."""
        mock_get_principal.return_value = "api-user-456"

        distinct_id = identity.get_distinct_id()

        assert distinct_id == "api-user-456"
        mock_get_principal.assert_called_once()

    @patch("arcade_core.usage.identity.UsageIdentity.get_principal_id")
    def test_returns_anon_id_when_not_authenticated(
        self, mock_get_principal: MagicMock, identity: UsageIdentity
    ) -> None:
        """Test that get_distinct_id returns anon_id when not authenticated."""
        mock_get_principal.return_value = None

        distinct_id = identity.get_distinct_id()
        data = identity.load_or_create()

        assert distinct_id == data["anon_id"]


class TestGetPrincipalId:
    """Tests for get_principal_id() method."""

    def test_returns_none_when_credentials_file_not_exists(self, identity: UsageIdentity) -> None:
        """Test that get_principal_id returns None when credentials file doesn't exist."""
        principal_id = identity.get_principal_id()

        assert principal_id is None

    @patch("httpx.get")
    def test_returns_principal_id_on_successful_api_call(
        self, mock_get: MagicMock, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that get_principal_id returns principal_id from API."""
        # Create credentials file
        credentials_file = temp_config_path / "credentials.yaml"
        credentials_file.write_text(yaml.dump({"cloud": {"api": {"key": "test-api-key"}}}))

        # Mock API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"principal_id": "api-principal-123"}}
        mock_get.return_value = mock_response

        principal_id = identity.get_principal_id()

        assert principal_id == "api-principal-123"
        mock_get.assert_called_once_with(
            "https://cloud.arcade.dev/api/v1/auth/validate",
            headers={"accept": "application/json", "Authorization": "Bearer test-api-key"},
            timeout=2.0,
        )

    @patch("httpx.get")
    def test_returns_none_on_api_failure(
        self, mock_get: MagicMock, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that get_principal_id returns None on API failure."""
        credentials_file = temp_config_path / "credentials.yaml"
        credentials_file.write_text(yaml.dump({"cloud": {"api": {"key": "test-api-key"}}}))

        mock_get.side_effect = Exception("Network error")

        principal_id = identity.get_principal_id()

        assert principal_id is None

    def test_returns_none_when_api_key_missing(
        self, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that get_principal_id returns None when API key is missing."""
        credentials_file = temp_config_path / "credentials.yaml"
        credentials_file.write_text(yaml.dump({"cloud": {}}))

        principal_id = identity.get_principal_id()

        assert principal_id is None

    @patch("httpx.get")
    def test_returns_none_on_non_200_status(
        self, mock_get: MagicMock, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that get_principal_id returns None on non-200 status code."""
        credentials_file = temp_config_path / "credentials.yaml"
        credentials_file.write_text(yaml.dump({"cloud": {"api": {"key": "test-api-key"}}}))

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        principal_id = identity.get_principal_id()

        assert principal_id is None

    @patch("httpx.get")
    def test_returns_account_id_from_oauth_whoami(
        self, mock_get: MagicMock, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that get_principal_id returns account_id using OAuth access token."""
        credentials_file = temp_config_path / "credentials.yaml"
        credentials_file.write_text(
            yaml.dump({"cloud": {"auth": {"access_token": "oauth-token", "refresh_token": "x"}}})
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"account_id": "acct-123"}}
        mock_get.return_value = mock_response

        principal_id = identity.get_principal_id()

        assert principal_id == "acct-123"
        mock_get.assert_called_once_with(
            "https://cloud.arcade.dev/api/v1/auth/whoami",
            headers={"accept": "application/json", "Authorization": "Bearer oauth-token"},
            timeout=2.0,
        )


class TestShouldAlias:
    """Tests for should_alias() method."""

    @patch("arcade_core.usage.identity.UsageIdentity.get_principal_id")
    def test_returns_true_when_authenticated_but_not_linked(
        self, mock_get_principal: MagicMock, identity: UsageIdentity
    ) -> None:
        """Test that should_alias returns True when user is authenticated but not yet aliased."""
        mock_get_principal.return_value = "new-principal-id"

        should_alias = identity.should_alias()

        assert should_alias is True

    @patch("arcade_core.usage.identity.UsageIdentity.get_principal_id")
    def test_returns_false_when_already_linked(
        self, mock_get_principal: MagicMock, identity: UsageIdentity, temp_config_path: Path
    ) -> None:
        """Test that should_alias returns False when principal_id already linked."""
        principal_id = "already-linked-123"
        mock_get_principal.return_value = principal_id

        usage_file = temp_config_path / "usage.json"
        usage_file.write_text(
            json.dumps({"anon_id": str(uuid.uuid4()), "linked_principal_id": principal_id})
        )

        should_alias = identity.should_alias()

        assert should_alias is False

    @patch("arcade_core.usage.identity.UsageIdentity.get_principal_id")
    def test_returns_false_when_not_authenticated(
        self, mock_get_principal: MagicMock, identity: UsageIdentity
    ) -> None:
        """Test that should_alias returns False when not authenticated."""
        mock_get_principal.return_value = None

        should_alias = identity.should_alias()

        assert should_alias is False


class TestResetToAnonymous:
    """Tests for reset_to_anonymous() method."""

    def test_generates_new_anon_id(self, identity: UsageIdentity) -> None:
        """Test that reset_to_anonymous generates a new anon_id."""
        original_data = identity.load_or_create()
        original_anon_id = original_data["anon_id"]

        identity.reset_to_anonymous()

        new_data = identity.load_or_create()
        assert new_data["anon_id"] != original_anon_id
        assert uuid.UUID(new_data["anon_id"])  # Validates UUID format

    def test_clears_linked_principal_id(self, identity: UsageIdentity) -> None:
        """Test that reset_to_anonymous clears linked_principal_id."""
        identity.set_linked_principal_id("user-to-clear")

        identity.reset_to_anonymous()

        data = identity.load_or_create()
        assert data["linked_principal_id"] is None

    def test_persists_to_file(self, identity: UsageIdentity, temp_config_path: Path) -> None:
        """Test that reset_to_anonymous persists changes to file."""
        identity.reset_to_anonymous()

        usage_file = temp_config_path / "usage.json"
        assert usage_file.exists()

        with usage_file.open() as f:
            file_data = json.load(f)

        assert "anon_id" in file_data
        assert file_data["linked_principal_id"] is None


class TestSetLinkedPrincipalId:
    """Tests for set_linked_principal_id() method."""

    def test_updates_linked_principal_id(self, identity: UsageIdentity) -> None:
        """Test that set_linked_principal_id updates the linked_principal_id."""
        identity.load_or_create()  # Initialize

        identity.set_linked_principal_id("new-user-789")

        data = identity.load_or_create()
        assert data["linked_principal_id"] == "new-user-789"

    def test_persists_to_file(self, identity: UsageIdentity, temp_config_path: Path) -> None:
        """Test that set_linked_principal_id persists changes to file."""
        identity.set_linked_principal_id("persisted-user-999")

        usage_file = temp_config_path / "usage.json"
        with usage_file.open() as f:
            file_data = json.load(f)

        assert file_data["linked_principal_id"] == "persisted-user-999"

    def test_updates_cache(self, identity: UsageIdentity) -> None:
        """Test that set_linked_principal_id updates the cached data."""
        identity.load_or_create()

        identity.set_linked_principal_id("cached-user-111")

        # Access _data directly to verify cache updated
        assert identity._data is not None
        assert identity._data["linked_principal_id"] == "cached-user-111"


class TestAnonIdProperty:
    """Tests for anon_id property."""

    def test_returns_anon_id(self, identity: UsageIdentity) -> None:
        """Test that anon_id property returns the anon_id."""
        data = identity.load_or_create()

        assert identity.anon_id == data["anon_id"]

    def test_returns_valid_uuid(self, identity: UsageIdentity) -> None:
        """Test that anon_id property returns a valid UUID."""
        anon_id = identity.anon_id

        assert uuid.UUID(anon_id)  # Validate UUID format
