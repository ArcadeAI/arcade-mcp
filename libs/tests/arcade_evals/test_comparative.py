"""Tests for comparative evaluation cases."""

import pytest
from arcade_evals import EvalSuite, ExpectedMCPToolCall
from arcade_evals._evalsuite._comparative import ComparativeCaseBuilder
from arcade_evals._evalsuite._types import (
    ComparativeCase,
    ExpectedToolCall,
    TrackConfig,
)

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestTrackConfig:
    """Tests for TrackConfig dataclass."""

    def test_create_track_config(self) -> None:
        """Test creating a TrackConfig."""
        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedMCPToolCall("TestTool", args={"arg1": "value1"})
        ]
        config = TrackConfig(expected_tool_calls=expected)

        assert config.expected_tool_calls == expected
        assert config.critics == []

    def test_create_track_config_with_critics(self) -> None:
        """Test creating a TrackConfig with critics."""
        from arcade_evals.critic import Critic, SimilarityCritic

        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedMCPToolCall("TestTool", args={"arg1": "value1"})
        ]
        critics: list[Critic] = [SimilarityCritic(critic_field="arg1", weight=1.0)]
        config = TrackConfig(expected_tool_calls=expected, critics=critics)

        assert config.expected_tool_calls == expected
        assert config.critics == critics


class TestComparativeCase:
    """Tests for ComparativeCase dataclass."""

    def test_create_comparative_case(self) -> None:
        """Test creating a ComparativeCase."""
        case = ComparativeCase(
            name="test_case",
            user_message="What's the weather?",
            system_message="You are helpful.",
        )

        assert case.name == "test_case"
        assert case.user_message == "What's the weather?"
        assert case.system_message == "You are helpful."
        assert case.additional_messages == []
        assert case.track_configs == {}

    def test_add_track_config(self) -> None:
        """Test adding track configuration."""
        case = ComparativeCase(
            name="test_case",
            user_message="What's the weather?",
        )
        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedMCPToolCall("GetWeather", args={"city": "NYC"})
        ]

        case.add_track_config("Track1", expected)

        assert "Track1" in case.track_configs
        assert case.track_configs["Track1"].expected_tool_calls == expected

    def test_add_duplicate_track_config_raises(self) -> None:
        """Test that adding duplicate track config raises."""
        case = ComparativeCase(
            name="test_case",
            user_message="What's the weather?",
        )
        expected1: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedMCPToolCall("Tool1", args={"arg": "v1"})
        ]
        expected2: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedMCPToolCall("Tool2", args={"arg": "v2"})
        ]

        case.add_track_config("Track1", expected1)

        with pytest.raises(ValueError, match="already configured"):
            case.add_track_config("Track1", expected2)

    def test_get_configured_tracks(self) -> None:
        """Test getting list of configured tracks."""
        case = ComparativeCase(
            name="test_case",
            user_message="What's the weather?",
        )
        track1: list[ExpectedToolCall | ExpectedMCPToolCall] = [ExpectedMCPToolCall("Tool1")]
        track2: list[ExpectedToolCall | ExpectedMCPToolCall] = [ExpectedMCPToolCall("Tool2")]
        case.add_track_config("Track1", track1)
        case.add_track_config("Track2", track2)

        tracks = case.get_configured_tracks()

        assert tracks == ["Track1", "Track2"]


class TestComparativeCaseBuilder:
    """Tests for ComparativeCaseBuilder fluent API."""

    def test_builder_creates_case(self) -> None:
        """Test builder creates a comparative case."""
        suite = EvalSuite(name="Test Suite", system_message="Test")
        # Register a track first
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")

        builder = ComparativeCaseBuilder(
            suite=suite,
            name="test_case",
            user_message="Test message",
            system_message="System message",
        )

        assert builder.case.name == "test_case"
        assert builder.case.user_message == "Test message"
        assert builder.case.system_message == "System message"

    def test_builder_for_track(self) -> None:
        """Test builder for_track method."""
        suite = EvalSuite(name="Test Suite", system_message="Test")
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")

        builder = ComparativeCaseBuilder(
            suite=suite,
            name="test_case",
            user_message="Test message",
        )

        result = builder.for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1", args={"arg": "value"})],
        )

        assert result is builder  # Returns self for chaining
        assert "Track1" in builder.case.track_configs

    def test_builder_for_track_nonexistent_raises(self) -> None:
        """Test for_track raises for nonexistent track."""
        suite = EvalSuite(name="Test Suite", system_message="Test")

        builder = ComparativeCaseBuilder(
            suite=suite,
            name="test_case",
            user_message="Test message",
        )

        with pytest.raises(ValueError, match="not found"):
            builder.for_track(
                "NonexistentTrack",
                expected_tool_calls=[ExpectedMCPToolCall("Tool1")],
            )

    def test_builder_chaining(self) -> None:
        """Test builder supports method chaining."""
        suite = EvalSuite(name="Test Suite", system_message="Test")
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")
        suite.add_tool_definitions([{"name": "Tool2"}], track="Track2")

        builder = ComparativeCaseBuilder(
            suite=suite,
            name="test_case",
            user_message="Test message",
        )

        builder.for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1")],
        ).for_track(
            "Track2",
            expected_tool_calls=[ExpectedMCPToolCall("Tool2")],
        )

        assert len(builder.case.track_configs) == 2
        assert "Track1" in builder.case.track_configs
        assert "Track2" in builder.case.track_configs

    def test_builder_build_empty_raises(self) -> None:
        """Test build raises when no tracks configured."""
        suite = EvalSuite(name="Test Suite", system_message="Test")

        builder = ComparativeCaseBuilder(
            suite=suite,
            name="test_case",
            user_message="Test message",
        )

        with pytest.raises(ValueError, match="No tracks configured"):
            builder.build()


class TestEvalSuiteTrackIntegration:
    """Tests for EvalSuite track integration."""

    def test_add_tool_definitions_with_track(self) -> None:
        """Test adding tool definitions to a specific track."""
        suite = EvalSuite(name="Test", system_message="Test")

        suite.add_tool_definitions(
            [{"name": "TestTool", "description": "A test"}],
            track="MyTrack",
        )

        tracks = suite.get_tracks()
        assert "MyTrack" in tracks
        assert suite.get_tool_count(track="MyTrack") == 1
        assert suite.list_tool_names(track="MyTrack") == ["TestTool"]

    def test_add_tool_definitions_multiple_tracks(self) -> None:
        """Test adding tools to multiple tracks."""
        suite = EvalSuite(name="Test", system_message="Test")

        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")
        suite.add_tool_definitions([{"name": "Tool2"}], track="Track2")

        assert len(suite.get_tracks()) == 2
        assert suite.list_tool_names(track="Track1") == ["Tool1"]
        assert suite.list_tool_names(track="Track2") == ["Tool2"]

    def test_tracks_are_isolated(self) -> None:
        """Test that tracks have isolated tool registries."""
        suite = EvalSuite(name="Test", system_message="Test")

        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")
        suite.add_tool_definitions([{"name": "Tool2"}], track="Track2")

        # Each track only sees its own tools
        track1_tools = suite.list_tool_names(track="Track1")
        track2_tools = suite.list_tool_names(track="Track2")

        assert "Tool1" in track1_tools
        assert "Tool2" not in track1_tools
        assert "Tool2" in track2_tools
        assert "Tool1" not in track2_tools

    def test_default_registry_separate_from_tracks(self) -> None:
        """Test that default registry is separate from tracks."""
        suite = EvalSuite(name="Test", system_message="Test")

        # Add to default registry
        suite.add_tool_definitions([{"name": "DefaultTool"}])
        # Add to track
        suite.add_tool_definitions([{"name": "TrackTool"}], track="MyTrack")

        # Default registry
        assert suite.get_tool_count() == 1
        assert suite.list_tool_names() == ["DefaultTool"]

        # Track registry
        assert suite.get_tool_count(track="MyTrack") == 1
        assert suite.list_tool_names(track="MyTrack") == ["TrackTool"]

    def test_add_comparative_case(self) -> None:
        """Test add_comparative_case method."""
        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")

        builder = suite.add_comparative_case(
            name="weather_query",
            user_message="What's the weather in NYC?",
        )

        assert builder is not None
        assert builder.case.name == "weather_query"

        # Configure track and verify
        builder.for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1", args={"city": "NYC"})],
        )

        assert "Track1" in builder.case.track_configs

    def test_add_comparative_case_uses_suite_defaults(self) -> None:
        """Test add_comparative_case uses suite defaults."""
        from arcade_evals import EvalRubric

        rubric = EvalRubric(fail_threshold=0.9)
        suite = EvalSuite(
            name="Test",
            system_message="Default system message",
            rubric=rubric,
        )

        builder = suite.add_comparative_case(
            name="test",
            user_message="Test message",
        )

        assert builder.case.system_message == "Default system message"
        assert builder.case.rubric == rubric

    def test_get_tracks_empty(self) -> None:
        """Test get_tracks when no tracks registered."""
        suite = EvalSuite(name="Test", system_message="Test")

        assert suite.get_tracks() == []

    def test_method_chaining_still_works(self) -> None:
        """Test that method chaining still works with track parameter."""
        suite = EvalSuite(name="Test", system_message="Test")

        # Chaining should still work
        result = suite.add_tool_definitions(
            [{"name": "Tool1"}],
            track="Track1",
        ).add_tool_definitions(
            [{"name": "Tool2"}],
            track="Track2",
        )

        assert result is suite
        assert len(suite.get_tracks()) == 2


class TestRunComparative:
    """Tests for EvalSuite.run_comparative method."""

    @pytest.mark.asyncio
    async def test_run_comparative_no_cases_raises(self) -> None:
        """Test run_comparative raises when no cases defined."""
        from unittest.mock import AsyncMock

        suite = EvalSuite(name="Test", system_message="Test")
        client = AsyncMock()

        with pytest.raises(ValueError, match="No comparative cases defined"):
            await suite.run_comparative(client, "gpt-4o")

    @pytest.mark.asyncio
    async def test_run_comparative_missing_track_raises(self) -> None:
        """Test builder raises when track doesn't exist (fail-fast validation)."""
        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")

        # Builder validates tracks exist at configuration time (fail-fast)
        builder = suite.add_comparative_case(
            name="test_case",
            user_message="Test",
        ).for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1")],
        )

        # Attempting to add non-existent track should raise immediately
        with pytest.raises(ValueError, match="Track 'NonExistentTrack' not found"):
            builder.for_track(
                "NonExistentTrack",
                expected_tool_calls=[ExpectedMCPToolCall("Tool2")],
            )

    @pytest.mark.asyncio
    async def test_run_comparative_no_tracks_configured_raises(self) -> None:
        """Test run_comparative raises when builder has no tracks."""
        from unittest.mock import AsyncMock

        suite = EvalSuite(name="Test", system_message="Test")
        # Add case but don't configure any tracks
        suite.add_comparative_case(
            name="test_case",
            user_message="Test",
        )

        client = AsyncMock()
        with pytest.raises(ValueError, match="No tracks configured"):
            await suite.run_comparative(client, "gpt-4o")

    @pytest.mark.asyncio
    async def test_run_comparative_basic_execution(self) -> None:
        """Test run_comparative executes cases across tracks."""
        from unittest.mock import AsyncMock, MagicMock

        suite = EvalSuite(name="Test Suite", system_message="You are helpful")

        # Register tools for two tracks
        suite.add_tool_definitions(
            [{"name": "GetWeather", "description": "Get weather"}],
            track="Track1",
        )
        suite.add_tool_definitions(
            [{"name": "FetchWeather", "description": "Fetch weather"}],
            track="Track2",
        )

        # Add comparative case
        suite.add_comparative_case(
            name="weather_query",
            user_message="What's the weather?",
        ).for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("GetWeather", args={"city": "NYC"})],
        ).for_track(
            "Track2",
            expected_tool_calls=[ExpectedMCPToolCall("FetchWeather", args={"city": "NYC"})],
        )

        # Mock OpenAI client
        client = AsyncMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "GetWeather"
        mock_tool_call.function.arguments = '{"city": "NYC"}'
        mock_message.tool_calls = [mock_tool_call]
        mock_response.choices = [MagicMock(message=mock_message)]
        client.chat.completions.create.return_value = mock_response

        # Run comparative evaluation
        results = await suite.run_comparative(client, "gpt-4o", provider="openai")

        # Verify structure
        assert "Track1" in results
        assert "Track2" in results
        assert results["Track1"]["model"] == "gpt-4o"
        assert results["Track1"]["suite_name"] == "Test Suite"
        assert results["Track1"]["track_name"] == "Track1"
        assert len(results["Track1"]["cases"]) == 1
        assert len(results["Track2"]["cases"]) == 1

        # Verify case results
        track1_case = results["Track1"]["cases"][0]
        assert track1_case["name"] == "weather_query"
        assert track1_case["track"] == "Track1"
        assert track1_case["input"] == "What's the weather?"
        assert "evaluation" in track1_case

    @pytest.mark.asyncio
    async def test_run_comparative_multiple_cases(self) -> None:
        """Test run_comparative with multiple comparative cases."""
        from unittest.mock import AsyncMock, MagicMock

        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")
        suite.add_tool_definitions([{"name": "Tool2"}], track="Track2")

        # Add two comparative cases
        suite.add_comparative_case(
            name="case1",
            user_message="Query 1",
        ).for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1")],
        ).for_track(
            "Track2",
            expected_tool_calls=[ExpectedMCPToolCall("Tool2")],
        )

        suite.add_comparative_case(
            name="case2",
            user_message="Query 2",
        ).for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1")],
        )

        # Mock client
        client = AsyncMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.tool_calls = []
        mock_response.choices = [MagicMock(message=mock_message)]
        client.chat.completions.create.return_value = mock_response

        results = await suite.run_comparative(client, "gpt-4o")

        # Verify both tracks present
        assert "Track1" in results
        assert "Track2" in results

        # Track1 should have 2 cases, Track2 should have 1 case
        assert len(results["Track1"]["cases"]) == 2
        assert len(results["Track2"]["cases"]) == 1

        # Verify case names
        track1_names = {case["name"] for case in results["Track1"]["cases"]}
        assert track1_names == {"case1", "case2"}
        track2_names = {case["name"] for case in results["Track2"]["cases"]}
        assert track2_names == {"case1"}

    @pytest.mark.asyncio
    async def test_run_comparative_anthropic_provider(self) -> None:
        """Test run_comparative with Anthropic provider."""
        from unittest.mock import AsyncMock, MagicMock

        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([{"name": "TestTool"}], track="Track1")

        suite.add_comparative_case(
            name="test",
            user_message="Test query",
        ).for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("TestTool")],
        )

        # Mock Anthropic client
        client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = []
        client.messages.create.return_value = mock_response

        results = await suite.run_comparative(client, "claude-3-5-sonnet", provider="anthropic")

        assert "Track1" in results
        assert len(results["Track1"]["cases"]) == 1
        # Verify Anthropic client was called
        assert client.messages.create.called

    @pytest.mark.asyncio
    async def test_run_comparative_track_deleted_after_config(self) -> None:
        """Test run_comparative when track is deleted after case configuration.

        This tests the execution-time validation that ensures tracks still exist
        when run_comparative is called (edge case for programmatic track deletion).
        """
        from unittest.mock import AsyncMock

        suite = EvalSuite(name="Test", system_message="Test")

        # Register track and configure case
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")
        suite.add_comparative_case(
            name="test_case",
            user_message="Test",
        ).for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1")],
        )

        # Simulate track being removed (edge case - programmatic deletion)
        # This bypasses builder validation but triggers run_comparative validation
        suite._track_manager._tracks.clear()

        client = AsyncMock()

        # Should raise at execution time with helpful error
        with pytest.raises(ValueError, match="Missing track registries.*Track1"):
            await suite.run_comparative(client, "gpt-4o")

    @pytest.mark.asyncio
    async def test_run_comparative_registry_none_defensive_check(self) -> None:
        """Test the defensive RuntimeError if registry is None after validation.

        This tests the defensive programming check that should never trigger
        in normal operation but protects against race conditions or bugs.
        """
        from unittest.mock import AsyncMock

        suite = EvalSuite(name="Test", system_message="Test")
        suite.add_tool_definitions([{"name": "Tool1"}], track="Track1")

        suite.add_comparative_case(
            name="test_case",
            user_message="Test",
        ).for_track(
            "Track1",
            expected_tool_calls=[ExpectedMCPToolCall("Tool1")],
        )

        client = AsyncMock()

        # Patch get_registry to return None during execution loop
        # has_track() will pass validation, but get_registry() will return None
        # This simulates a race condition where track is deleted between validation and execution
        original_has_track = suite._track_manager.has_track

        def patched_get_registry(track_name: str) -> None:
            # Return None to trigger the defensive check
            return None

        def patched_has_track(track_name: str) -> bool:
            # Return True to pass validation
            return original_has_track(track_name)

        # Apply patches using patch.object to satisfy mypy
        from unittest.mock import patch

        with (
            patch.object(suite._track_manager, "get_registry", patched_get_registry),
            patch.object(suite._track_manager, "has_track", patched_has_track),
        ):
            # Should raise RuntimeError (defensive check)
            with pytest.raises(RuntimeError, match="Registry.*unexpectedly None after validation"):
                await suite.run_comparative(client, "gpt-4o")
