"""Tests for track management in comparative evaluations."""

import pytest
from arcade_evals._evalsuite._tool_registry import EvalSuiteToolRegistry
from arcade_evals._evalsuite._tracks import TrackManager

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestTrackManager:
    """Tests for TrackManager class."""

    def test_create_track(self) -> None:
        """Test creating a new track."""
        manager = TrackManager()
        registry = EvalSuiteToolRegistry()

        track_name = manager.create_track("Test Track", registry)

        assert track_name == "Test Track"
        assert manager.has_track("Test Track")
        assert manager.track_count() == 1

    def test_create_duplicate_track_raises(self) -> None:
        """Test that creating a duplicate track raises ValueError."""
        manager = TrackManager()
        registry1 = EvalSuiteToolRegistry()
        registry2 = EvalSuiteToolRegistry()

        manager.create_track("Track1", registry1)

        with pytest.raises(ValueError, match="already exists"):
            manager.create_track("Track1", registry2)

    def test_get_registry(self) -> None:
        """Test getting a registry by track name."""
        manager = TrackManager()
        registry = EvalSuiteToolRegistry()
        registry.add_tool({"name": "TestTool", "description": "Test"})

        manager.create_track("MyTrack", registry)
        retrieved = manager.get_registry("MyTrack")

        assert retrieved is registry
        assert retrieved.has_tool("TestTool")

    def test_get_registry_nonexistent(self) -> None:
        """Test getting a nonexistent registry returns None."""
        manager = TrackManager()

        result = manager.get_registry("NonexistentTrack")

        assert result is None

    def test_get_track_names(self) -> None:
        """Test getting all track names."""
        manager = TrackManager()
        manager.create_track("Track1", EvalSuiteToolRegistry())
        manager.create_track("Track2", EvalSuiteToolRegistry())
        manager.create_track("Track3", EvalSuiteToolRegistry())

        names = manager.get_track_names()

        assert names == ["Track1", "Track2", "Track3"]

    def test_get_track_names_empty(self) -> None:
        """Test getting track names when empty."""
        manager = TrackManager()

        names = manager.get_track_names()

        assert names == []

    def test_has_track(self) -> None:
        """Test checking if track exists."""
        manager = TrackManager()
        manager.create_track("Exists", EvalSuiteToolRegistry())

        assert manager.has_track("Exists") is True
        assert manager.has_track("DoesNotExist") is False

    def test_track_count(self) -> None:
        """Test counting tracks."""
        manager = TrackManager()

        assert manager.track_count() == 0

        manager.create_track("Track1", EvalSuiteToolRegistry())
        assert manager.track_count() == 1

        manager.create_track("Track2", EvalSuiteToolRegistry())
        assert manager.track_count() == 2

    def test_get_all_registries(self) -> None:
        """Test getting all registries."""
        manager = TrackManager()
        reg1 = EvalSuiteToolRegistry()
        reg2 = EvalSuiteToolRegistry()

        manager.create_track("Track1", reg1)
        manager.create_track("Track2", reg2)

        all_regs = manager.get_all_registries()

        assert len(all_regs) == 2
        assert all_regs["Track1"] is reg1
        assert all_regs["Track2"] is reg2

    def test_registries_are_isolated(self) -> None:
        """Test that each track has its own isolated registry."""
        manager = TrackManager()
        reg1 = EvalSuiteToolRegistry()
        reg2 = EvalSuiteToolRegistry()

        reg1.add_tool({"name": "Tool1", "description": "Tool for track 1"})
        reg2.add_tool({"name": "Tool2", "description": "Tool for track 2"})

        manager.create_track("Track1", reg1)
        manager.create_track("Track2", reg2)

        # Each registry only has its own tool
        assert manager.get_registry("Track1").has_tool("Tool1")
        assert not manager.get_registry("Track1").has_tool("Tool2")
        assert manager.get_registry("Track2").has_tool("Tool2")
        assert not manager.get_registry("Track2").has_tool("Tool1")
