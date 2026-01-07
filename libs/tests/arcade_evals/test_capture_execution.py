"""Tests for capture mode execution."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_evals import EvalSuite

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestCaptureMode:
    """Tests for EvalSuite.capture() method."""

    @pytest.mark.asyncio
    async def test_capture_records_tool_calls_without_scoring(self) -> None:
        """Test that capture mode records tool calls without evaluation."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {"name": "search", "description": "Search", "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }}
        ])
        suite.add_case(name="test case", user_message="search for cats", expected_tool_calls=[])

        mock_client = AsyncMock()
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "search"
        mock_tool_call.function.arguments = '{"query": "cats"}'

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [mock_tool_call]
        mock_client.chat.completions.create.return_value = mock_response

        result = await suite.capture(mock_client, "gpt-4o", provider="openai")

        # Should return CaptureResult with captured_cases
        assert result.suite_name == "test"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"
        assert len(result.captured_cases) == 1

        captured = result.captured_cases[0]
        # Should have recorded the tool call
        assert len(captured.tool_calls) == 1
        assert captured.tool_calls[0].name == "search"
        assert captured.tool_calls[0].args == {"query": "cats"}

    @pytest.mark.asyncio
    async def test_capture_raises_without_tools(self) -> None:
        """Test that capture mode raises error when no tools registered."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_case(name="test", user_message="test", expected_tool_calls=[])

        mock_client = AsyncMock()

        with pytest.raises(ValueError, match="No tools registered"):
            await suite.capture(mock_client, "gpt-4o", provider="openai")

    @pytest.mark.asyncio
    async def test_capture_works_with_anthropic_provider(self) -> None:
        """Test capture mode works with Anthropic provider."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([{"name": "search", "description": "Search", "inputSchema": {}}])
        suite.add_case(name="test", user_message="test", expected_tool_calls=[])

        mock_client = AsyncMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "search"
        mock_tool_block.input = {"query": "test"}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_client.messages.create.return_value = mock_response

        result = await suite.capture(mock_client, "claude-3", provider="anthropic")

        assert len(result.captured_cases) == 1
        assert len(result.captured_cases[0].tool_calls) == 1

    @pytest.mark.asyncio
    async def test_capture_respects_max_concurrent(self) -> None:
        """Test that capture mode respects max_concurrent setting."""
        suite = EvalSuite(name="test", system_message="test", max_concurrent=2)
        suite.add_tool_definitions([{"name": "tool1", "description": "Test", "inputSchema": {}}])

        # Add 3 cases
        for i in range(3):
            suite.add_case(name=f"case{i}", user_message=f"test{i}", expected_tool_calls=[])

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None
        mock_client.chat.completions.create.return_value = mock_response

        result = await suite.capture(mock_client, "gpt-4o", provider="openai")

        # All 3 cases should be captured
        assert len(result.captured_cases) == 3
