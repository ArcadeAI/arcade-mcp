from unittest.mock import MagicMock, patch

import pytest
from arcade_core.errors import ToolkitLoadError
from arcade_core.toolkit import Toolkit


class TestToolkit:
    """Test the Toolkit class functionality."""

    def test_strip_arcade_prefix_validator(self):
        """Test that the name validator strips the arcade_ prefix."""
        toolkit = Toolkit(
            name="arcade_test",
            package_name="arcade_test",
            description="Test toolkit",
            version="1.0.0",
        )
        assert toolkit.name == "test"

    def test_no_arcade_prefix_unchanged(self):
        """Test that names without arcade_ prefix remain unchanged."""
        toolkit = Toolkit(
            name="mytest",
            package_name="mytest",
            description="Test toolkit",
            version="1.0.0",
        )
        assert toolkit.name == "mytest"

    def test_strip_arcade_prefix_method(self):
        """Test the _strip_arcade_prefix static method."""
        assert Toolkit._strip_arcade_prefix("arcade_test") == "test"
        assert Toolkit._strip_arcade_prefix("test") == "test"
        assert Toolkit._strip_arcade_prefix("arcade_my_toolkit") == "my_toolkit"
        assert Toolkit._strip_arcade_prefix("myarcade_toolkit") == "myarcade_toolkit"
        assert Toolkit._strip_arcade_prefix("") == ""
        assert Toolkit._strip_arcade_prefix("arcade_") == ""


class TestFromEntrypoint:
    """Test the from_entrypoint class method."""

    @patch("arcade_core.toolkit.Toolkit.from_package")
    def test_from_entrypoint_success(self, mock_from_package):
        """Test successful creation of toolkit from entry point."""
        # Create mock entry point with dist
        mock_entry = MagicMock()
        mock_entry.value = "my_toolkit"
        mock_entry.name = "toolkit_name"
        mock_entry.dist = MagicMock()
        mock_entry.dist.name = "my-toolkit"

        # Mock the from_package return
        mock_toolkit = Toolkit(
            name="my_toolkit",
            package_name="my-toolkit",
            version="1.2.3",
            description="My test toolkit",
            author=["Test Author"],
            homepage="https://github.com/test/toolkit",
        )
        mock_from_package.return_value = mock_toolkit

        toolkit = Toolkit.from_entrypoint(mock_entry)

        mock_from_package.assert_called_once_with("my-toolkit")
        assert toolkit.name == "my_toolkit"
        assert toolkit.package_name == "my-toolkit"

    def test_from_entrypoint_no_dist(self):
        """Test handling when entry point has no dist attribute."""
        # Create mock entry point without dist
        mock_entry = MagicMock()
        mock_entry.value = "my_toolkit"
        mock_entry.name = "toolkit_name"
        mock_entry.dist = None

        with pytest.raises(ToolkitLoadError, match="does not have distribution metadata"):
            Toolkit.from_entrypoint(mock_entry)


class TestFindArcadeToolkitsFromEntrypoints:
    """Test the find_arcade_toolkits_from_entrypoints method."""

    @patch("arcade_core.toolkit.importlib.metadata.entry_points")
    @patch("arcade_core.toolkit.Toolkit.from_entrypoint")
    def test_find_from_entrypoints_success(self, mock_from_ep, mock_entry_points):
        """Test successful discovery of toolkits from entry points."""
        # Create mock entry points
        mock_ep1 = MagicMock()
        mock_ep1.name = "toolkit_name"
        mock_ep1.value = "toolkit1"
        mock_ep2 = MagicMock()
        mock_ep2.name = "toolkit_name"
        mock_ep2.value = "toolkit2"

        mock_entry_points.return_value = [mock_ep1, mock_ep2]

        # Create mock toolkits
        toolkit1 = Toolkit(
            name="toolkit1",
            package_name="toolkit1",
            version="1.0.0",
            description="Toolkit 1",
        )
        toolkit2 = Toolkit(
            name="toolkit2",
            package_name="toolkit2",
            version="1.0.0",
            description="Toolkit 2",
        )
        mock_from_ep.side_effect = [toolkit1, toolkit2]

        toolkits = Toolkit.find_arcade_toolkits_from_entrypoints()

        assert len(toolkits) == 2
        assert toolkits[0].name == "toolkit1"
        assert toolkits[1].name == "toolkit2"

    @patch("arcade_core.toolkit.importlib.metadata.entry_points")
    @patch("arcade_core.toolkit.Toolkit.from_entrypoint")
    def test_find_from_entrypoints_with_errors(self, mock_from_ep, mock_entry_points):
        """Test that errors in loading individual toolkits are handled gracefully."""
        # Create mock entry points
        mock_ep1 = MagicMock()
        mock_ep1.name = "toolkit_name"
        mock_ep1.value = "toolkit1"
        mock_ep2 = MagicMock()
        mock_ep2.name = "toolkit_name"
        mock_ep2.value = "toolkit2"
        mock_ep3 = MagicMock()
        mock_ep3.name = "toolkit_name"
        mock_ep3.value = "toolkit3"
        mock_entry_points.return_value = [mock_ep1, mock_ep2, mock_ep3]

        # Create mock toolkits
        toolkit1 = Toolkit(
            name="toolkit1",
            package_name="toolkit1",
            version="1.0.0",
            description="Toolkit 1",
        )
        toolkit3 = Toolkit(
            name="toolkit3",
            package_name="toolkit3",
            version="1.0.0",
            description="Toolkit 3",
        )
        mock_from_ep.side_effect = [toolkit1, ToolkitLoadError("Failed to load toolkit2"), toolkit3]

        toolkits = Toolkit.find_arcade_toolkits_from_entrypoints()

        assert len(toolkits) == 2
        assert toolkits[0].name == "toolkit1"
        assert toolkits[1].name == "toolkit3"

    @patch("arcade_core.toolkit.importlib.metadata.entry_points")
    def test_find_from_entrypoints_no_group(self, mock_entry_points):
        """Test when arcade_toolkits entry point group doesn't exist."""
        # Mock entry_points to return empty list
        mock_entry_points.return_value = []

        # Test
        toolkits = Toolkit.find_arcade_toolkits_from_entrypoints()

        assert toolkits == []


class TestFindAllArcadeToolkits:
    """Test the combined toolkit discovery method."""

    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_entrypoints")
    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_prefix")
    def test_find_all_no_duplicates(self, mock_find_prefix, mock_find_ep):
        """Test that find_all returns combined results without duplicates."""
        # Create mock toolkits
        toolkit1 = Toolkit(
            name="toolkit1",
            package_name="toolkit1",
            version="1.0.0",
            description="Toolkit 1",
        )
        toolkit2 = Toolkit(
            name="toolkit2",
            package_name="toolkit2",
            version="1.0.0",
            description="Toolkit 2",
        )
        # Mock the discovery methods
        mock_find_ep.return_value = [toolkit1]
        mock_find_prefix.return_value = [toolkit2]

        toolkits = Toolkit.find_all_arcade_toolkits()

        assert len(toolkits) == 2
        assert any(t.name == "toolkit1" for t in toolkits)
        assert any(t.name == "toolkit2" for t in toolkits)

    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_entrypoints")
    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_prefix")
    def test_find_all_with_duplicates_prefers_entrypoint(self, mock_find_prefix, mock_find_ep):
        """Test that entry point toolkits are preferred over prefix-based ones."""
        toolkit_ep = Toolkit(
            name="test",
            package_name="arcade_test",  # Same package name
            version="2.0.0",
            description="Entry point version",
        )

        toolkit_prefix = Toolkit(
            name="test",
            package_name="arcade_test",  # Same package name
            version="1.0.0",
            description="Prefix version",
        )
        # Mock the discovery methods
        mock_find_ep.return_value = [toolkit_ep]
        mock_find_prefix.return_value = [toolkit_prefix]

        toolkits = Toolkit.find_all_arcade_toolkits()

        assert len(toolkits) == 1
        assert toolkits[0].version == "2.0.0"
        assert toolkits[0].description == "Entry point version"

    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_entrypoints")
    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_prefix")
    def test_find_all_empty(self, mock_find_prefix, mock_find_ep):
        """Test when no toolkits are found."""
        mock_find_ep.return_value = []
        mock_find_prefix.return_value = []

        toolkits = Toolkit.find_all_arcade_toolkits()
        assert toolkits == []


class TestEntryPointCompatibility:
    """Test compatibility scenarios for entry point discovery."""

    @patch("arcade_core.toolkit.importlib.metadata.entry_points")
    @patch("arcade_core.toolkit.Toolkit.from_entrypoint")
    def test_duplicate_toolkit_names_in_entrypoints(self, mock_from_ep, mock_entry_points):
        """Test handling of duplicate toolkit names in entry points."""
        # Create mock entry points with same name
        mock_ep1 = MagicMock()
        mock_ep1.name = "toolkit_name"
        mock_ep1.value = "test_v1"

        mock_ep2 = MagicMock()
        mock_ep2.name = "toolkit_name"
        mock_ep2.value = "test_v2"

        mock_entry_points.return_value = [mock_ep1, mock_ep2]

        # Mock toolkit creation - both with same toolkit name
        toolkit1 = Toolkit(
            name="test",
            package_name="test_v1",
            version="1.0.0",
            description="Test v1",
        )

        toolkit2 = Toolkit(
            name="test",
            package_name="test_v2",
            version="2.0.0",
            description="Test v2",
        )

        mock_from_ep.side_effect = [toolkit1, toolkit2]

        # Should return both even with same display name
        toolkits = Toolkit.find_arcade_toolkits_from_entrypoints()
        assert len(toolkits) == 2

    @patch("arcade_core.toolkit.Toolkit.from_package")
    def test_from_entrypoint_with_arcade_prefix(self, mock_from_package):
        """Test that arcade_ prefix is stripped from entry point toolkits."""
        # Create mock entry point
        mock_entry = MagicMock()
        mock_entry.value = "arcade_example"
        mock_entry.name = "toolkit_name"
        mock_entry.dist = MagicMock()
        mock_entry.dist.name = "arcade-example"

        # Mock the from_package return
        mock_toolkit = Toolkit(
            name="arcade_example",
            package_name="arcade-example",
            version="1.0.0",
            description="Example toolkit",
        )
        mock_from_package.return_value = mock_toolkit

        toolkit = Toolkit.from_entrypoint(mock_entry)

        assert toolkit.name == "example"
        assert toolkit.package_name == "arcade-example"


class TestToolkitIntegration:
    """Integration tests for toolkit discovery and loading."""

    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_entrypoints")
    @patch("arcade_core.toolkit.Toolkit.find_arcade_toolkits_from_prefix")
    def test_mixed_toolkit_sources(self, mock_find_prefix, mock_find_ep):
        """Test discovering toolkits from both sources with various naming patterns."""
        # Create toolkits with different naming patterns
        ep_toolkit1 = Toolkit(
            name="custom",
            package_name="my_custom_toolkit",
            version="1.0.0",
            description="Custom toolkit",
        )
        ep_toolkit2 = Toolkit(
            name="utils",
            package_name="arcade_utils",
            version="2.0.0",
            description="Utils toolkit",
        )
        prefix_toolkit1 = Toolkit(
            name="legacy",
            package_name="arcade_legacy",
            version="1.0.0",
            description="Legacy toolkit",
        )
        prefix_toolkit2 = Toolkit(
            name="utils",
            package_name="arcade_utils",  # Same package name as ep_toolkit2
            version="0.9.0",
            description="Old utils toolkit",
        )
        mock_find_ep.return_value = [ep_toolkit1, ep_toolkit2]
        mock_find_prefix.return_value = [prefix_toolkit1, prefix_toolkit2]

        toolkits = Toolkit.find_all_arcade_toolkits()

        # Should have 3 toolkits (ep_toolkit2 supersedes prefix_toolkit2 due to same package_name)
        assert len(toolkits) == 3
        names = {t.name for t in toolkits}
        assert names == {"custom", "utils", "legacy"}
        utils_toolkit = next(t for t in toolkits if t.name == "utils")
        assert utils_toolkit.version == "2.0.0"
