import sys
from unittest.mock import MagicMock, patch

import pytest
from arcade_cli.usage.command_tracker import CommandTracker


class MockCommand:
    """Mock Typer command for testing."""

    def __init__(self, name: str) -> None:
        self.name = name


class MockContext:
    """Mock Typer context for testing."""

    def __init__(self, name: str, parent: "MockContext | None" = None) -> None:
        self.command = MockCommand(name)
        self.parent = parent


@pytest.fixture
def mock_dependencies() -> dict:
    """Mock all external dependencies for CommandTracker."""
    with (
        patch("arcade_cli.usage.command_tracker.UsageService") as mock_service_cls,
        patch("arcade_cli.usage.command_tracker.UsageIdentity") as mock_identity_cls,
        patch("arcade_cli.usage.command_tracker.is_tracking_enabled") as mock_tracking,
    ):
        # Setup mock instances
        mock_service = MagicMock()
        mock_service_cls.return_value = mock_service

        mock_identity = MagicMock()
        mock_identity_cls.return_value = mock_identity
        mock_identity.anon_id = "anon-123"

        mock_tracking.return_value = True

        yield {
            "service_cls": mock_service_cls,
            "service": mock_service,
            "identity_cls": mock_identity_cls,
            "identity": mock_identity,
            "tracking": mock_tracking,
        }


class TestCliVersion:
    """Tests for cli_version property."""

    @patch("arcade_cli.usage.command_tracker.metadata.version")
    def test_returns_version_on_success(self, mock_version: MagicMock) -> None:
        """Test that cli_version returns the version from metadata."""
        mock_version.return_value = "1.2.3"

        tracker = CommandTracker()

        assert tracker.cli_version == "1.2.3"

    @patch("arcade_cli.usage.command_tracker.metadata.version")
    def test_returns_unknown_on_exception(self, mock_version: MagicMock) -> None:
        """Test that cli_version returns 'unknown' when metadata fails."""
        mock_version.side_effect = Exception("Package not found")

        tracker = CommandTracker()

        assert tracker.cli_version == "unknown"


class TestRuntimeLanguage:
    """Tests for runtime_language property."""

    def test_returns_python(self) -> None:
        """Test that runtime_language returns 'python'."""
        tracker = CommandTracker()

        assert tracker.runtime_language == "python"


class TestRuntimeVersion:
    """Tests for runtime_version property."""

    def test_matches_sys_version_info(self) -> None:
        """Test that runtime_version matches sys.version_info."""
        tracker = CommandTracker()

        version = tracker.runtime_version
        expected = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        assert version == expected

    def test_caches_version(self) -> None:
        """Test that runtime_version caches the version after first access."""
        tracker = CommandTracker()

        first_access = tracker.runtime_version
        second_access = tracker.runtime_version

        # Should return the same object b/c it's cached
        assert first_access is second_access


class TestUserId:
    """Tests for user_id property."""

    def test_delegates_to_identity(self, mock_dependencies: dict) -> None:
        """Test that user_id delegates to identity.get_distinct_id()."""
        mock_dependencies["identity"].get_distinct_id.return_value = "user-456"

        tracker = CommandTracker()

        assert tracker.user_id == "user-456"
        mock_dependencies["identity"].get_distinct_id.assert_called_once()


class TestGetFullCommandPath:
    """Tests for get_full_command_path() method."""

    def test_single_command(self) -> None:
        """Test get_full_command_path with a single command."""
        ctx = MockContext("login", parent=MockContext("root"))

        tracker = CommandTracker()
        path = tracker.get_full_command_path(ctx)

        assert path == "login"

    def test_nested_commands(self) -> None:
        """Test get_full_command_path with nested commands."""
        root = MockContext("root")
        toolkit = MockContext("toolkit", parent=root)
        list_cmd = MockContext("list", parent=toolkit)

        tracker = CommandTracker()
        path = tracker.get_full_command_path(list_cmd)

        assert path == "toolkit.list"

    def test_deeply_nested_commands(self) -> None:
        """Test get_full_command_path with deeply nested commands."""
        root = MockContext("root")
        level1 = MockContext("level1", parent=root)
        level2 = MockContext("level2", parent=level1)
        level3 = MockContext("level3", parent=level2)

        tracker = CommandTracker()
        path = tracker.get_full_command_path(level3)

        assert path == "level1.level2.level3"

    def test_root_command_no_parent(self) -> None:
        """Test get_full_command_path with root command (no parent)."""
        ctx = MockContext("root", parent=None)

        tracker = CommandTracker()
        path = tracker.get_full_command_path(ctx)

        assert path == ""


class TestHandleSuccessfulLogin:
    """Tests for _handle_successful_login() method."""

    def test_aliases_when_should_alias_true(self, mock_dependencies: dict) -> None:
        """Test that login aliases anon_id to principal_id when should_alias is True."""
        mock_dependencies["identity"].get_principal_id.return_value = "principal-789"
        mock_dependencies["identity"].should_alias.return_value = True
        mock_dependencies["identity"].anon_id = "anon-456"

        tracker = CommandTracker()
        tracker._handle_successful_login()

        mock_dependencies["service"].alias.assert_called_once_with(
            previous_id="anon-456", distinct_id="principal-789"
        )

    def test_does_not_alias_when_should_alias_false(self, mock_dependencies: dict) -> None:
        """Test that login does not alias when should_alias is False."""
        mock_dependencies["identity"].get_principal_id.return_value = "principal-789"
        mock_dependencies["identity"].should_alias.return_value = False

        tracker = CommandTracker()
        tracker._handle_successful_login()

        mock_dependencies["service"].alias.assert_not_called()

    def test_always_sets_linked_principal_id(self, mock_dependencies: dict) -> None:
        """Test that login always sets linked_principal_id on success."""
        mock_dependencies["identity"].get_principal_id.return_value = "principal-999"
        mock_dependencies["identity"].should_alias.return_value = False

        tracker = CommandTracker()
        tracker._handle_successful_login()

        mock_dependencies["identity"].set_linked_principal_id.assert_called_once_with(
            "principal-999"
        )

    def test_does_nothing_when_no_principal_id(self, mock_dependencies: dict) -> None:
        """Test that login does nothing when principal_id is None."""
        mock_dependencies["identity"].get_principal_id.return_value = None

        tracker = CommandTracker()
        tracker._handle_successful_login()

        mock_dependencies["service"].alias.assert_not_called()
        mock_dependencies["identity"].set_linked_principal_id.assert_not_called()


class TestHandleSuccessfulLogout:
    """Tests for _handle_successful_logout() method."""

    @patch("arcade_cli.usage.command_tracker.platform")
    def test_sends_logout_event(self, mock_platform: MagicMock, mock_dependencies: dict) -> None:
        """Test that logout sends a logout event."""
        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "23.4.0"
        mock_dependencies["identity"].load_or_create.return_value = {
            "linked_principal_id": "user-123"
        }
        mock_dependencies["identity"].get_distinct_id.return_value = "user-123"

        tracker = CommandTracker()
        tracker._handle_successful_logout("logout", duration_ms=100.5)

        mock_dependencies["service"].capture.assert_called_once()
        call_args = mock_dependencies["service"].capture.call_args

        assert call_args[0][0] == "CLI execution succeeded"
        assert call_args[0][1] == "user-123"
        assert call_args[1]["properties"]["command_name"] == "logout"
        assert call_args[1]["properties"]["duration_ms"] == round(100.5)

    def test_resets_to_anonymous_when_was_authenticated(self, mock_dependencies: dict) -> None:
        """Test that logout resets to anonymous when user was authenticated."""
        mock_dependencies["identity"].load_or_create.return_value = {
            "linked_principal_id": "user-123"
        }
        mock_dependencies["identity"].get_distinct_id.return_value = "user-123"

        tracker = CommandTracker()
        tracker._handle_successful_logout("logout")

        mock_dependencies["identity"].reset_to_anonymous.assert_called_once()

    def test_does_not_reset_when_not_authenticated(self, mock_dependencies: dict) -> None:
        """Test that logout does not reset anon_id when user was not authenticated."""
        mock_dependencies["identity"].load_or_create.return_value = {"linked_principal_id": None}
        mock_dependencies["identity"].get_distinct_id.return_value = "anon-123"

        tracker = CommandTracker()
        tracker._handle_successful_logout("logout")

        mock_dependencies["identity"].reset_to_anonymous.assert_not_called()

    @patch("arcade_cli.usage.command_tracker.platform")
    def test_includes_duration_when_provided(
        self, mock_platform: MagicMock, mock_dependencies: dict
    ) -> None:
        """Test that logout includes duration in event properties."""
        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "23.4.0"
        mock_dependencies["identity"].load_or_create.return_value = {"linked_principal_id": None}
        mock_dependencies["identity"].get_distinct_id.return_value = "anon-123"

        tracker = CommandTracker()
        tracker._handle_successful_logout("logout", duration_ms=250.75)

        call_args = mock_dependencies["service"].capture.call_args
        assert call_args[1]["properties"]["duration_ms"] == round(250.75)


class TestTrackCommandExecution:
    """Tests for track_command_execution() method."""

    def test_does_nothing_when_tracking_disabled(self, mock_dependencies: dict) -> None:
        """Test that track_command_execution does nothing when tracking is disabled."""
        mock_dependencies["tracking"].return_value = False

        tracker = CommandTracker()
        tracker.track_command_execution("test.command", success=True)

        mock_dependencies["service"].capture.assert_not_called()

    @patch("arcade_cli.usage.command_tracker.platform")
    def test_tracks_successful_command(
        self, mock_platform: MagicMock, mock_dependencies: dict
    ) -> None:
        """Test that successful command execution is tracked."""
        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "23.4.0"
        mock_dependencies["identity"].get_distinct_id.return_value = "user-789"
        mock_dependencies["identity"].anon_id = "anon-456"

        tracker = CommandTracker()
        tracker.track_command_execution("test.command", success=True, duration_ms=50.25)

        mock_dependencies["service"].capture.assert_called_once()
        call_args = mock_dependencies["service"].capture.call_args

        assert call_args[0][0] == "CLI execution succeeded"
        assert call_args[0][1] == "user-789"
        assert call_args[1]["properties"]["command_name"] == "test.command"
        assert call_args[1]["properties"]["duration_ms"] == round(50.25)

    @patch("arcade_cli.usage.command_tracker.platform")
    def test_tracks_failed_command(self, mock_platform: MagicMock, mock_dependencies: dict) -> None:
        """Test that failed command execution is tracked."""
        mock_platform.system.return_value = "Linux"
        mock_platform.release.return_value = "5.15.0"
        mock_dependencies["identity"].get_distinct_id.return_value = "user-999"
        mock_dependencies["identity"].anon_id = "anon-888"

        tracker = CommandTracker()
        tracker.track_command_execution(
            "failed.command", success=False, error_message="Something went wrong"
        )

        mock_dependencies["service"].capture.assert_called_once()
        call_args = mock_dependencies["service"].capture.call_args

        assert call_args[0][0] == "CLI execution failed"
        assert call_args[1]["properties"]["error_message"] == "Something went wrong"

    def test_handles_login_command(self, mock_dependencies: dict) -> None:
        """Test that login command triggers _handle_successful_login."""
        mock_dependencies["identity"].get_principal_id.return_value = "principal-123"
        mock_dependencies["identity"].should_alias.return_value = True
        mock_dependencies["identity"].anon_id = "anon-789"

        tracker = CommandTracker()
        tracker.track_command_execution("login", success=True, is_login=True)

        # Should call alias as part of login handling
        mock_dependencies["service"].alias.assert_called_once()

    def test_handles_logout_command(self, mock_dependencies: dict) -> None:
        """Test that logout command triggers _handle_successful_logout."""
        mock_dependencies["identity"].load_or_create.return_value = {
            "linked_principal_id": "user-123"
        }
        mock_dependencies["identity"].get_distinct_id.return_value = "user-123"

        tracker = CommandTracker()
        tracker.track_command_execution("logout", success=True, is_logout=True)

        # Should reset to anonymous as part of logout handling
        mock_dependencies["identity"].reset_to_anonymous.assert_called_once()

    def test_lazy_alias_check_on_other_commands(self, mock_dependencies: dict) -> None:
        """Test that non-login commands trigger lazy alias check."""
        mock_dependencies["identity"].should_alias.return_value = True
        mock_dependencies["identity"].get_principal_id.return_value = "principal-456"
        mock_dependencies["identity"].anon_id = "anon-999"
        mock_dependencies["identity"].get_distinct_id.return_value = "principal-456"

        tracker = CommandTracker()
        tracker.track_command_execution("other.command", success=True)

        # Should call alias due to lazy check
        mock_dependencies["service"].alias.assert_called_once_with(
            previous_id="anon-999", distinct_id="principal-456"
        )

    def test_rounds_duration_to_two_decimals(self, mock_dependencies: dict) -> None:
        """Test that duration is rounded to 2 decimal places."""
        mock_dependencies["identity"].get_distinct_id.return_value = "user-123"
        mock_dependencies["identity"].anon_id = "anon-456"

        tracker = CommandTracker()
        tracker.track_command_execution("test", success=True, duration_ms=123.456789)

        call_args = mock_dependencies["service"].capture.call_args
        assert call_args[1]["properties"]["duration_ms"] == round(123.46)

    @patch("arcade_cli.usage.command_tracker.platform")
    def test_sets_is_anon_flag_correctly(
        self, mock_platform: MagicMock, mock_dependencies: dict
    ) -> None:
        """Test that is_anon flag is set correctly."""
        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "23.4.0"
        mock_dependencies["identity"].get_distinct_id.return_value = "anon-123"
        mock_dependencies["identity"].anon_id = "anon-123"

        tracker = CommandTracker()
        tracker.track_command_execution("test", success=True)

        call_args = mock_dependencies["service"].capture.call_args
        assert call_args[1]["is_anon"] is True

    @patch("arcade_cli.usage.command_tracker.platform")
    def test_is_anon_false_for_authenticated_user(
        self, mock_platform: MagicMock, mock_dependencies: dict
    ) -> None:
        """Test that is_anon is False for authenticated users."""
        mock_platform.system.return_value = "Darwin"
        mock_platform.release.return_value = "23.4.0"
        mock_dependencies["identity"].get_distinct_id.return_value = "user-authenticated"
        mock_dependencies["identity"].anon_id = "anon-123"

        tracker = CommandTracker()
        tracker.track_command_execution("test", success=True)

        call_args = mock_dependencies["service"].capture.call_args
        assert call_args[1]["is_anon"] is False

    @patch("arcade_cli.usage.command_tracker.platform")
    def test_includes_os_info_in_properties(
        self, mock_platform: MagicMock, mock_dependencies: dict
    ) -> None:
        """Test that OS information is included in event properties."""
        mock_platform.system.return_value = "Windows"
        mock_platform.release.return_value = "10"
        mock_dependencies["identity"].get_distinct_id.return_value = "user-123"
        mock_dependencies["identity"].anon_id = "anon-456"

        tracker = CommandTracker()
        tracker.track_command_execution("test", success=True)

        call_args = mock_dependencies["service"].capture.call_args
        properties = call_args[1]["properties"]

        assert properties["os_type"] == "Windows"
        assert properties["os_release"] == "10"

    def test_does_not_include_duration_when_not_provided(self, mock_dependencies: dict) -> None:
        """Test that duration is not included in properties when not provided."""
        mock_dependencies["identity"].get_distinct_id.return_value = "user-123"
        mock_dependencies["identity"].anon_id = "anon-456"

        tracker = CommandTracker()
        tracker.track_command_execution("test", success=True)

        call_args = mock_dependencies["service"].capture.call_args
        properties = call_args[1]["properties"]

        assert "duration_ms" not in properties
