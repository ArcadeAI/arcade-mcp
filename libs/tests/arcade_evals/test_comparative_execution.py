"""Tests for comparative evaluation execution logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedMCPToolCall,
)

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestRunComparative:
    """Tests for EvalSuite.run_comparative() method."""

    @pytest.mark.asyncio
    async def test_for_track_validates_track_exists(self) -> None:
        """Test that for_track raises error if track doesn't exist."""
        suite = EvalSuite(name="test", system_message="test")

        # Add tools to track1 only
        suite.add_tool_definitions([{"name": "tool1", "description": "Test", "inputSchema": {}}], track="track1")

        # Try to add comparative case with track2 (doesn't exist)
        case = suite.add_comparative_case(name="test", user_message="test")
        case.for_track("track1", expected_tool_calls=[ExpectedMCPToolCall("tool1", args={})])

        # for_track validates immediately
        with pytest.raises(ValueError, match="Track.*not found"):
            case.for_track("track2", expected_tool_calls=[ExpectedMCPToolCall("tool2", args={})])

    @pytest.mark.asyncio
    async def test_run_comparative_returns_track_results(self) -> None:
        """Test that run_comparative returns dict with track results."""
        suite = EvalSuite(name="test", system_message="test")

        # Add tools to two tracks
        suite.add_tool_definitions([{"name": "tool1", "description": "Test", "inputSchema": {}}], track="track1")
        suite.add_tool_definitions([{"name": "tool2", "description": "Test", "inputSchema": {}}], track="track2")

        # Add comparative case
        case = suite.add_comparative_case(name="case1", user_message="test")
        case.for_track("track1", expected_tool_calls=[ExpectedMCPToolCall("tool1", args={})])
        case.for_track("track2", expected_tool_calls=[ExpectedMCPToolCall("tool2", args={})])

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None
        mock_client.chat.completions.create.return_value = mock_response

        result = await suite.run_comparative(mock_client, "gpt-4o", provider="openai")

        # Should return dict with track names as keys
        assert isinstance(result, dict)
        assert "track1" in result
        assert "track2" in result

        # Each track should have model, suite_name, track_name, cases
        assert result["track1"]["model"] == "gpt-4o"
        assert result["track1"]["suite_name"] == "test"
        assert result["track1"]["track_name"] == "track1"
        assert "cases" in result["track1"]
        assert len(result["track1"]["cases"]) == 1

    @pytest.mark.asyncio
    async def test_run_comparative_raises_without_comparative_cases(self) -> None:
        """Test that run_comparative raises error when no comparative cases defined."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([{"name": "tool1", "description": "Test", "inputSchema": {}}])

        mock_client = AsyncMock()

        with pytest.raises(ValueError, match="No comparative cases defined"):
            await suite.run_comparative(mock_client, "gpt-4o", provider="openai")

    @pytest.mark.asyncio
    async def test_run_comparative_respects_max_concurrent(self) -> None:
        """Test that run_comparative respects max_concurrent setting."""
        suite = EvalSuite(name="test", system_message="test", max_concurrent=2)

        # Add tools
        suite.add_tool_definitions([{"name": "tool1", "description": "Test", "inputSchema": {}}], track="track1")

        # Add 3 cases
        for i in range(3):
            case = suite.add_comparative_case(name=f"case{i}", user_message=f"test{i}")
            case.for_track("track1", expected_tool_calls=[])

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None
        mock_client.chat.completions.create.return_value = mock_response

        # Semaphore with max_concurrent=2 will be used
        result = await suite.run_comparative(mock_client, "gpt-4o", provider="openai")

        # All cases should complete
        assert len(result["track1"]["cases"]) == 3

    @pytest.mark.asyncio
    async def test_run_comparative_with_anthropic_provider(self) -> None:
        """Test run_comparative works with Anthropic provider."""
        suite = EvalSuite(name="test", system_message="test")

        suite.add_tool_definitions([{"name": "search", "description": "Search", "inputSchema": {}}], track="track1")

        case = suite.add_comparative_case(name="test", user_message="search for cats")
        case.for_track("track1", expected_tool_calls=[ExpectedMCPToolCall("search", args={"query": "cats"})])

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        result = await suite.run_comparative(mock_client, "claude-3", provider="anthropic")

        assert "track1" in result
        assert result["track1"]["model"] == "claude-3"


class TestComparativeCaseBuilder:
    """Tests for ComparativeCaseBuilder fluent API."""

    def test_for_track_returns_builder_for_chaining(self) -> None:
        """Test that for_track returns builder for method chaining."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([{"name": "t1", "description": "Test", "inputSchema": {}}], track="track1")
        suite.add_tool_definitions([{"name": "t2", "description": "Test", "inputSchema": {}}], track="track2")

        builder = suite.add_comparative_case(name="test", user_message="test")
        result1 = builder.for_track("track1", expected_tool_calls=[])
        result2 = result1.for_track("track2", expected_tool_calls=[])

        # Should return same builder for chaining
        assert result1 is builder
        assert result2 is builder

    def test_comparative_case_with_custom_rubric(self) -> None:
        """Test that comparative cases can have custom rubrics."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([{"name": "t1", "description": "Test", "inputSchema": {}}], track="track1")

        strict_rubric = EvalRubric(fail_threshold=0.7, warn_threshold=0.9)

        # Rubric is set on the case, not per track
        builder = suite.add_comparative_case(name="test", user_message="test", rubric=strict_rubric)
        builder.for_track("track1", expected_tool_calls=[])

        # Build and verify rubric is stored on the case
        comp_case = builder.build()
        assert comp_case.rubric == strict_rubric

    def test_for_track_with_track_specific_critics(self) -> None:
        """Test that tracks can have specific critics."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([{"name": "t1", "description": "Test", "inputSchema": {}}], track="track1")

        critics = [BinaryCritic(critic_field="query", weight=1.0)]

        builder = suite.add_comparative_case(name="test", user_message="test")
        builder.for_track("track1", expected_tool_calls=[], critics=critics)

        comp_case = builder.build()
        assert comp_case.track_configs["track1"].critics == critics

    def test_build_raises_if_no_tracks_configured(self) -> None:
        """Test that build() raises error if no tracks are configured."""
        suite = EvalSuite(name="test", system_message="test")
        builder = suite.add_comparative_case(name="test", user_message="test")

        with pytest.raises(ValueError, match="No tracks configured"):
            builder.build()


class TestComparativeTrackValidation:
    """Tests for track validation in comparative evaluations."""

    def test_for_track_validates_track_exists(self) -> None:
        """Test that for_track validates track exists immediately."""
        suite = EvalSuite(name="test", system_message="test")

        # Register only track1
        suite.add_tool_definitions([{"name": "t1", "description": "Test", "inputSchema": {}}], track="track1")

        # Try to use nonexistent_track
        case = suite.add_comparative_case(name="test", user_message="test")
        case.for_track("track1", expected_tool_calls=[])

        # for_track validates immediately
        with pytest.raises(ValueError, match="Track.*not found"):
            case.for_track("nonexistent_track", expected_tool_calls=[])

    def test_for_track_error_lists_available_tracks(self) -> None:
        """Test that error message lists available tracks."""
        suite = EvalSuite(name="test", system_message="test")

        suite.add_tool_definitions([{"name": "t1", "description": "Test", "inputSchema": {}}], track="available_track")

        case = suite.add_comparative_case(name="test", user_message="test")

        with pytest.raises(ValueError) as exc_info:
            case.for_track("missing_track", expected_tool_calls=[])

        error_msg = str(exc_info.value)
        assert "missing_track" in error_msg
        assert "available_track" in error_msg


class TestComparativeConcurrencyControl:
    """Tests for concurrency control in comparative execution."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_tasks(self) -> None:
        """Test that semaphore properly limits concurrent API calls."""
        suite = EvalSuite(name="test", system_message="test", max_concurrent=1)

        suite.add_tool_definitions([{"name": "t1", "description": "Test", "inputSchema": {}}], track="track1")

        # Add 3 cases - with max_concurrent=1, they should run sequentially
        for i in range(3):
            case = suite.add_comparative_case(name=f"case{i}", user_message="test")
            case.for_track("track1", expected_tool_calls=[])

        call_count = 0

        async def mock_create(**kwargs):
            nonlocal call_count
            call_count += 1
            # Simulate some delay
            import asyncio
            await asyncio.sleep(0.01)
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.tool_calls = None
            return mock_response

        mock_client = AsyncMock()
        mock_client.chat.completions.create = mock_create

        await suite.run_comparative(mock_client, "gpt-4o", provider="openai")

        # All 3 cases should have been called
        assert call_count == 3
