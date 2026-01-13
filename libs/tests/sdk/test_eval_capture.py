"""
Tests for EvalSuite capture mode functionality.

Capture mode allows running evaluations without scoring - it simply records
the tool calls made by the model for debugging or generating expected calls.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcade_evals import (
    CapturedCase,
    CapturedToolCall,
    CaptureResult,
    EvalSuite,
)

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals

# --- CapturedToolCall Tests ---


class TestCapturedToolCall:
    """Tests for CapturedToolCall dataclass."""

    def test_create_with_name_and_args(self):
        """Test creating a captured tool call with name and args."""
        tc = CapturedToolCall(name="Weather_GetCurrent", args={"location": "London"})
        assert tc.name == "Weather_GetCurrent"
        assert tc.args == {"location": "London"}

    def test_create_with_name_only(self):
        """Test creating a captured tool call with default empty args."""
        tc = CapturedToolCall(name="Weather_GetCurrent")
        assert tc.name == "Weather_GetCurrent"
        assert tc.args == {}

    def test_to_dict(self):
        """Test to_dict serialization."""
        tc = CapturedToolCall(name="MyTool", args={"key": "value"})
        result = tc.to_dict()
        assert result == {"name": "MyTool", "args": {"key": "value"}}

    def test_to_dict_empty_args(self):
        """Test to_dict with empty args."""
        tc = CapturedToolCall(name="MyTool")
        result = tc.to_dict()
        assert result == {"name": "MyTool", "args": {}}


# --- CapturedCase Tests ---


class TestCapturedCase:
    """Tests for CapturedCase dataclass."""

    def test_create_basic(self):
        """Test creating a captured case with minimal fields."""
        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[CapturedToolCall(name="Tool1")],
        )
        assert case.case_name == "test_case"
        assert case.user_message == "Hello"
        assert len(case.tool_calls) == 1
        assert case.system_message is None
        assert case.additional_messages is None

    def test_create_with_context(self):
        """Test creating a captured case with full context."""
        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[CapturedToolCall(name="Tool1")],
            system_message="You are an assistant",
            additional_messages=[{"role": "assistant", "content": "Hi"}],
        )
        assert case.system_message == "You are an assistant"
        assert case.additional_messages == [{"role": "assistant", "content": "Hi"}]

    def test_to_dict_without_context(self):
        """Test to_dict without including context."""
        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[CapturedToolCall(name="Tool1", args={"x": 1})],
            system_message="System message",
            additional_messages=[{"role": "user", "content": "msg"}],
        )
        result = case.to_dict(include_context=False)
        assert result == {
            "case_name": "test_case",
            "user_message": "Hello",
            "tool_calls": [{"name": "Tool1", "args": {"x": 1}}],
        }
        # Context should NOT be included
        assert "system_message" not in result
        assert "additional_messages" not in result

    def test_to_dict_with_context(self):
        """Test to_dict including context."""
        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[CapturedToolCall(name="Tool1", args={"x": 1})],
            system_message="System message",
            additional_messages=[{"role": "user", "content": "msg"}],
        )
        result = case.to_dict(include_context=True)
        assert result == {
            "case_name": "test_case",
            "user_message": "Hello",
            "tool_calls": [{"name": "Tool1", "args": {"x": 1}}],
            "system_message": "System message",
            "additional_messages": [{"role": "user", "content": "msg"}],
        }

    def test_to_dict_with_context_null_messages(self):
        """Test to_dict with context when additional_messages is None."""
        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[],
            system_message="Sys",
            additional_messages=None,
        )
        result = case.to_dict(include_context=True)
        assert result["additional_messages"] == []

    def test_to_dict_normalizes_json_string_arguments(self):
        """Test that JSON string arguments in additional_messages are parsed into objects."""
        # This simulates OpenAI's format where arguments is a JSON string
        additional_messages = [
            {"role": "user", "content": "List projects"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "Linear_ListProjects",
                            "arguments": '{"state": "started"}',  # JSON string
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"projects": []}',
                "tool_call_id": "call_123",
            },
        ]

        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[],
            system_message="Sys",
            additional_messages=additional_messages,
        )
        result = case.to_dict(include_context=True)

        # Arguments should be parsed into an object, not a string
        assistant_msg = result["additional_messages"][1]
        assert assistant_msg["tool_calls"][0]["function"]["arguments"] == {"state": "started"}

    def test_to_dict_handles_invalid_json_arguments(self):
        """Test that invalid JSON arguments are kept as strings."""
        additional_messages = [
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "SomeTool",
                            "arguments": "not valid json {",  # Invalid JSON
                        },
                    }
                ],
            },
        ]

        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[],
            system_message="Sys",
            additional_messages=additional_messages,
        )
        result = case.to_dict(include_context=True)

        # Invalid JSON should remain as string
        assistant_msg = result["additional_messages"][0]
        assert assistant_msg["tool_calls"][0]["function"]["arguments"] == "not valid json {"

    def test_to_dict_normalizes_tool_response_content(self):
        """Test that JSON content in tool response messages is parsed into objects."""
        additional_messages = [
            {"role": "user", "content": "Get the initiative"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_get_init",
                        "type": "function",
                        "function": {
                            "name": "Linear_GetInitiative",
                            "arguments": '{"id": "init_123"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": '{"id": "init_123", "name": "Q1 Goals", "status": "Planned"}',
                "tool_call_id": "call_get_init",
                "name": "Linear_GetInitiative",
            },
        ]

        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[],
            system_message="Sys",
            additional_messages=additional_messages,
        )
        result = case.to_dict(include_context=True)

        # Tool call arguments should be parsed
        assistant_msg = result["additional_messages"][1]
        assert assistant_msg["tool_calls"][0]["function"]["arguments"] == {"id": "init_123"}

        # Tool response content should be parsed
        tool_msg = result["additional_messages"][2]
        assert tool_msg["content"] == {"id": "init_123", "name": "Q1 Goals", "status": "Planned"}

    def test_to_dict_keeps_non_json_tool_content_as_string(self):
        """Test that non-JSON tool content is kept as string."""
        additional_messages = [
            {
                "role": "tool",
                "content": "Error: Tool not found",  # Plain text, not JSON
                "tool_call_id": "call_123",
                "name": "SomeTool",
            },
        ]

        case = CapturedCase(
            case_name="test_case",
            user_message="Hello",
            tool_calls=[],
            system_message="Sys",
            additional_messages=additional_messages,
        )
        result = case.to_dict(include_context=True)

        # Non-JSON content should remain as string
        tool_msg = result["additional_messages"][0]
        assert tool_msg["content"] == "Error: Tool not found"

    def test_empty_tool_calls(self):
        """Test case with no tool calls."""
        case = CapturedCase(
            case_name="no_tools",
            user_message="Just chat",
            tool_calls=[],
        )
        result = case.to_dict()
        assert result["tool_calls"] == []


# --- CaptureResult Tests ---


class TestCaptureResult:
    """Tests for CaptureResult dataclass."""

    def test_create_basic(self):
        """Test creating a capture result."""
        result = CaptureResult(
            suite_name="My Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[
                CapturedCase(
                    case_name="case1",
                    user_message="Hello",
                    tool_calls=[CapturedToolCall(name="Tool1")],
                )
            ],
        )
        assert result.suite_name == "My Suite"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"
        assert len(result.captured_cases) == 1

    def test_to_dict_without_context(self):
        """Test to_dict without context."""
        result = CaptureResult(
            suite_name="Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[
                CapturedCase(
                    case_name="case1",
                    user_message="Hello",
                    tool_calls=[CapturedToolCall(name="Tool1", args={"a": 1})],
                    system_message="System",
                )
            ],
        )
        d = result.to_dict(include_context=False)
        assert d["suite_name"] == "Suite"
        assert d["model"] == "gpt-4o"
        assert d["provider"] == "openai"
        assert len(d["captured_cases"]) == 1
        assert "system_message" not in d["captured_cases"][0]

    def test_to_dict_with_context(self):
        """Test to_dict with context."""
        result = CaptureResult(
            suite_name="Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[
                CapturedCase(
                    case_name="case1",
                    user_message="Hello",
                    tool_calls=[],
                    system_message="System",
                    additional_messages=[],
                )
            ],
        )
        d = result.to_dict(include_context=True)
        assert d["captured_cases"][0]["system_message"] == "System"

    def test_to_json(self):
        """Test JSON serialization."""
        result = CaptureResult(
            suite_name="Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[
                CapturedCase(
                    case_name="case1",
                    user_message="Hello",
                    tool_calls=[CapturedToolCall(name="Tool1")],
                )
            ],
        )
        json_str = result.to_json(include_context=False)
        parsed = json.loads(json_str)
        assert parsed["suite_name"] == "Suite"
        assert parsed["model"] == "gpt-4o"

    def test_to_json_with_indent(self):
        """Test JSON serialization with custom indent."""
        result = CaptureResult(
            suite_name="Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[],
        )
        json_str = result.to_json(indent=4)
        # Check that indentation is present (4 spaces)
        assert "    " in json_str

    def test_write_to_file(self):
        """Test writing capture result to file."""
        result = CaptureResult(
            suite_name="Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[
                CapturedCase(
                    case_name="case1",
                    user_message="Hello",
                    tool_calls=[CapturedToolCall(name="Tool1", args={"x": 1})],
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "capture_output.json"
            result.write_to_file(str(filepath))

            # Verify file was created and has valid content
            assert filepath.exists()
            with open(filepath) as f:
                data = json.load(f)
            assert data["suite_name"] == "Suite"
            assert len(data["captured_cases"]) == 1

    def test_write_to_file_with_context(self):
        """Test writing capture result with context to file."""
        result = CaptureResult(
            suite_name="Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[
                CapturedCase(
                    case_name="case1",
                    user_message="Hello",
                    tool_calls=[],
                    system_message="System",
                    additional_messages=[{"role": "user", "content": "x"}],
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "capture_output.json"
            result.write_to_file(str(filepath), include_context=True)

            with open(filepath) as f:
                data = json.load(f)
            assert data["captured_cases"][0]["system_message"] == "System"

    def test_empty_captured_cases(self):
        """Test with no captured cases."""
        result = CaptureResult(
            suite_name="Empty Suite",
            model="gpt-4o",
            provider="openai",
            captured_cases=[],
        )
        d = result.to_dict()
        assert d["captured_cases"] == []


# --- Imports Test ---


class TestCaptureImports:
    """Tests for capture mode imports."""

    def test_import_from_arcade_evals(self):
        """Test that capture classes are importable from arcade_evals."""
        from arcade_evals import CapturedCase, CapturedToolCall, CaptureResult

        assert CapturedToolCall is not None
        assert CapturedCase is not None
        assert CaptureResult is not None


# --- EvalSuite.capture() Tests ---


class TestEvalSuiteCapture:
    """Tests for EvalSuite.capture() method."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = AsyncMock()
        # Create mock response with tool calls
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [MagicMock()]
        mock_response.choices[0].message.tool_calls[0].function.name = "Weather_GetCurrent"
        mock_response.choices[0].message.tool_calls[0].function.arguments = '{"location": "London"}'
        client.chat.completions.create = AsyncMock(return_value=mock_response)
        return client

    @pytest.fixture
    def basic_suite(self):
        """Create a basic EvalSuite with a tool and case."""
        suite = EvalSuite(
            name="Test Suite",
            system_message="You are a helpful assistant",
        )
        suite.add_tool_definitions([
            {"name": "Weather_GetCurrent", "description": "Get weather", "inputSchema": {}}
        ])
        suite.add_case(
            name="test_case",
            user_message="What's the weather in London?",
            expected_tool_calls=[],  # No expectations in capture mode
        )
        return suite

    @pytest.mark.asyncio
    async def test_capture_returns_capture_result(self, basic_suite, mock_openai_client):
        """Test that capture() returns a CaptureResult."""
        result = await basic_suite.capture(
            client=mock_openai_client,
            model="gpt-4o",
            provider="openai",
        )
        assert isinstance(result, CaptureResult)
        assert result.suite_name == "Test Suite"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"

    @pytest.mark.asyncio
    async def test_capture_records_tool_calls(self, basic_suite, mock_openai_client):
        """Test that capture() records tool calls from model."""
        result = await basic_suite.capture(
            client=mock_openai_client,
            model="gpt-4o",
            provider="openai",
        )
        assert len(result.captured_cases) == 1
        case = result.captured_cases[0]
        assert case.case_name == "test_case"
        assert len(case.tool_calls) == 1
        assert case.tool_calls[0].name == "Weather_GetCurrent"
        assert case.tool_calls[0].args == {"location": "London"}

    @pytest.mark.asyncio
    async def test_capture_without_context(self, basic_suite, mock_openai_client):
        """Test that capture() without context doesn't include system message."""
        result = await basic_suite.capture(
            client=mock_openai_client,
            model="gpt-4o",
            provider="openai",
            include_context=False,
        )
        case = result.captured_cases[0]
        assert case.system_message is None
        assert case.additional_messages is None

    @pytest.mark.asyncio
    async def test_capture_with_context(self, basic_suite, mock_openai_client):
        """Test that capture() with context includes system message."""
        result = await basic_suite.capture(
            client=mock_openai_client,
            model="gpt-4o",
            provider="openai",
            include_context=True,
        )
        case = result.captured_cases[0]
        assert case.system_message == "You are a helpful assistant"
        assert case.additional_messages is not None

    @pytest.mark.asyncio
    async def test_capture_requires_tools(self):
        """Test that capture() raises error when no tools registered."""
        suite = EvalSuite(
            name="Empty Suite",
            system_message="Test",
        )
        suite.add_case(
            name="test_case",
            user_message="Hello",
            expected_tool_calls=[],
        )

        mock_client = AsyncMock()
        with pytest.raises(ValueError, match="No tools registered"):
            await suite.capture(mock_client, "gpt-4o", provider="openai")

    @pytest.mark.asyncio
    async def test_capture_multiple_cases(self, mock_openai_client):
        """Test capture with multiple cases."""
        suite = EvalSuite(
            name="Multi Case Suite",
            system_message="You are an assistant",
        )
        suite.add_tool_definitions([
            {"name": "Tool1", "description": "Tool 1"},
            {"name": "Tool2", "description": "Tool 2"},
        ])
        suite.add_case(name="case1", user_message="Do thing 1", expected_tool_calls=[])
        suite.add_case(name="case2", user_message="Do thing 2", expected_tool_calls=[])

        result = await suite.capture(
            client=mock_openai_client,
            model="gpt-4o",
            provider="openai",
        )
        assert len(result.captured_cases) == 2
        assert result.captured_cases[0].case_name == "case1"
        assert result.captured_cases[1].case_name == "case2"

    @pytest.mark.asyncio
    async def test_capture_no_tool_calls(self):
        """Test capture when model doesn't call any tools."""
        suite = EvalSuite(
            name="No Calls Suite",
            system_message="Test",
        )
        suite.add_tool_definitions([{"name": "Tool1", "description": "Tool 1"}])
        suite.add_case(name="case1", user_message="Hello", expected_tool_calls=[])

        # Mock client that returns no tool calls
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await suite.capture(
            client=mock_client,
            model="gpt-4o",
            provider="openai",
        )
        assert len(result.captured_cases) == 1
        assert len(result.captured_cases[0].tool_calls) == 0

    @pytest.mark.asyncio
    async def test_capture_normalizes_tool_calls(self, mock_openai_client):
        """Test that capture() normalizes tool names and fills defaults."""
        suite = EvalSuite(
            name="Normalization Suite",
            system_message="Test",
        )
        # Add tool with default arg
        suite.add_tool_definitions([
            {
                "name": "My.Tool",
                "description": "Tool with default",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "arg1": {"type": "string", "default": "default_val"},
                        "arg2": {"type": "string"},
                    },
                },
            }
        ])
        suite.add_case(name="case1", user_message="Call it", expected_tool_calls=[])

        # Mock client returning tool call with underscored name and missing default arg
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = [MagicMock()]

        tool_call = mock_response.choices[0].message.tool_calls[0]
        tool_call.function.name = "My_Tool"  # Normalized name
        tool_call.function.arguments = '{"arg2": "provided"}'  # Missing arg1

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await suite.capture(
            client=mock_openai_client,
            model="gpt-4o",
            provider="openai",
        )

        case = result.captured_cases[0]
        # Name is resolved to original format (My_Tool -> My.Tool)
        # This ensures consistency with expected tool names
        assert case.tool_calls[0].name == "My.Tool"
        # Args should include default value
        assert case.tool_calls[0].args == {"arg1": "default_val", "arg2": "provided"}


# --- tool_eval decorator capture mode Tests ---


class TestToolEvalCaptureMode:
    """Tests for tool_eval decorator with capture mode."""

    @pytest.mark.asyncio
    async def test_tool_eval_capture_mode_flag(self):
        """Test that tool_eval wrapper passes capture_mode correctly."""
        from arcade_evals import tool_eval

        @tool_eval()
        def my_eval():
            suite = EvalSuite(
                name="Test Suite",
                system_message="Test",
            )
            suite.add_tool_definitions([{"name": "Tool1", "description": "D"}])
            suite.add_case(name="case1", user_message="Hello", expected_tool_calls=[])
            return suite

        # Mock the underlying capture functions
        with patch("arcade_evals.eval._capture_with_openai") as mock_capture:
            mock_capture.return_value = CaptureResult(
                suite_name="Test",
                model="gpt-4o",
                provider="openai",
                captured_cases=[],
            )

            results = await my_eval(
                provider_api_key="test-key",
                model="gpt-4o",
                capture_mode=True,
                include_context=False,
            )

            mock_capture.assert_called_once()
            assert len(results) == 1
            assert isinstance(results[0], CaptureResult)

    @pytest.mark.asyncio
    async def test_tool_eval_capture_mode_with_context(self):
        """Test that tool_eval wrapper passes include_context correctly."""
        from arcade_evals import tool_eval

        @tool_eval()
        def my_eval():
            suite = EvalSuite(
                name="Test Suite",
                system_message="Test",
            )
            suite.add_tool_definitions([{"name": "Tool1", "description": "D"}])
            suite.add_case(name="case1", user_message="Hello", expected_tool_calls=[])
            return suite

        with patch("arcade_evals.eval._capture_with_openai") as mock_capture:
            mock_capture.return_value = CaptureResult(
                suite_name="Test",
                model="gpt-4o",
                provider="openai",
                captured_cases=[],
            )

            await my_eval(
                provider_api_key="test-key",
                model="gpt-4o",
                capture_mode=True,
                include_context=True,
            )

            # Verify include_context was passed
            call_args = mock_capture.call_args
            assert call_args[0][3] is True  # include_context is 4th positional arg


# --- Multiple Tool Calls per Case Tests ---


class TestMultipleToolCalls:
    """Tests for capturing multiple tool calls from a single case."""

    @pytest.mark.asyncio
    async def test_capture_multiple_tool_calls(self):
        """Test capturing multiple tool calls from one model response."""
        suite = EvalSuite(
            name="Multi Tool Suite",
            system_message="Test",
        )
        suite.add_tool_definitions([
            {"name": "Tool1", "description": "D1"},
            {"name": "Tool2", "description": "D2"},
        ])
        suite.add_case(name="case1", user_message="Do both", expected_tool_calls=[])

        # Mock client returning multiple tool calls
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]

        tool_call_1 = MagicMock()
        tool_call_1.function.name = "Tool1"
        tool_call_1.function.arguments = '{"arg1": "val1"}'

        tool_call_2 = MagicMock()
        tool_call_2.function.name = "Tool2"
        tool_call_2.function.arguments = '{"arg2": "val2"}'

        mock_response.choices[0].message.tool_calls = [tool_call_1, tool_call_2]
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await suite.capture(
            client=mock_client,
            model="gpt-4o",
            provider="openai",
        )

        assert len(result.captured_cases) == 1
        case = result.captured_cases[0]
        assert len(case.tool_calls) == 2
        assert case.tool_calls[0].name == "Tool1"
        assert case.tool_calls[0].args == {"arg1": "val1"}
        assert case.tool_calls[1].name == "Tool2"
        assert case.tool_calls[1].args == {"arg2": "val2"}


class TestCaptureWithAnthropic:
    """Tests for capture mode with Anthropic provider."""

    @pytest.mark.asyncio
    async def test_capture_with_anthropic_provider(self):
        """Test capture mode using Anthropic provider."""
        suite = EvalSuite(
            name="Anthropic Capture Suite",
            system_message="Test system message",
        )
        suite.add_tool_definitions([
            {"name": "Google.Search", "description": "Search"},
        ])
        suite.add_case(
            name="test_case",
            user_message="Search for something",
            expected_tool_calls=[],
        )

        # Mock Anthropic client
        mock_client = AsyncMock()
        mock_response = MagicMock()

        # Anthropic returns tool_use blocks
        mock_tool_use = MagicMock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "Google_Search"  # Anthropic uses underscores
        mock_tool_use.input = {"query": "test"}

        mock_response.content = [mock_tool_use]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await suite.capture(
            client=mock_client,
            model="claude-3-opus",
            provider="anthropic",
        )

        assert result.provider == "anthropic"
        assert len(result.captured_cases) == 1
        # Should resolve Google_Search back to Google.Search
        assert result.captured_cases[0].tool_calls[0].name == "Google.Search"


class TestCaptureHelperFunctions:
    """Tests for _capture_with_openai and _capture_with_anthropic helpers."""

    @pytest.mark.asyncio
    async def test_capture_with_openai_helper(self):
        """Test the _capture_with_openai helper function."""
        from arcade_evals.capture import _capture_with_openai

        suite = EvalSuite(
            name="OpenAI Helper Test",
            system_message="Test",
        )
        suite.add_tool_definitions([{"name": "TestTool", "description": "A test tool"}])
        suite.add_case(name="case1", user_message="Test", expected_tool_calls=[])

        # Mock the suite.capture method directly instead of AsyncOpenAI
        mock_result = CaptureResult(
            suite_name="OpenAI Helper Test",
            provider="openai",
            model="gpt-4o",
            captured_cases=[
                CapturedCase(
                    case_name="case1",
                    user_message="Test",
                    tool_calls=[],
                    system_message="Test",
                    additional_messages=[],
                )
            ],
        )

        with patch.object(suite, "capture", return_value=mock_result) as mock_capture:
            result = await _capture_with_openai(
                suite=suite,
                api_key="test-key",
                model="gpt-4o",
                include_context=True,
            )

            assert result.suite_name == "OpenAI Helper Test"
            assert result.provider == "openai"
            # Verify capture was called with correct arguments
            mock_capture.assert_called_once()
            call_args = mock_capture.call_args
            # Arguments: (client, model, provider=..., include_context=...)
            assert call_args.args[1] == "gpt-4o"  # model
            assert call_args.kwargs.get("provider") == "openai"
            assert call_args.kwargs.get("include_context") is True

    def test_capture_with_anthropic_function_exists(self):
        """Test that _capture_with_anthropic helper function exists and is callable."""
        # Verify the function exists and has the expected signature
        import inspect

        from arcade_evals.capture import _capture_with_anthropic

        sig = inspect.signature(_capture_with_anthropic)
        params = list(sig.parameters.keys())
        assert "suite" in params
        assert "api_key" in params
        assert "model" in params
        assert "include_context" in params
