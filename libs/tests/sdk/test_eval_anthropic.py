"""Tests for Anthropic provider support in evaluations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arcade_cli.utils import DEFAULT_MODELS, Provider, get_default_model, resolve_provider_api_key
from arcade_evals._evalsuite._providers import convert_messages_to_anthropic
from arcade_evals.eval import (
    EvalCase,
    EvalRubric,
    EvalSuite,
    ProviderName,
    _run_with_openai,
    compare_tool_name,
    normalize_name,
    tool_eval,
)

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestProviderEnum:
    """Tests for Provider enum."""

    def test_provider_has_openai(self) -> None:
        """Test that Provider enum has OPENAI value."""
        assert Provider.OPENAI.value == "openai"

    def test_provider_has_anthropic(self) -> None:
        """Test that Provider enum has ANTHROPIC value."""
        assert Provider.ANTHROPIC.value == "anthropic"

    def test_provider_values(self) -> None:
        """Test all provider values."""
        assert set(p.value for p in Provider) == {"openai", "anthropic"}


class TestDefaultModels:
    """Tests for default model selection per provider."""

    def test_default_models_constant_has_all_providers(self) -> None:
        """Test that DEFAULT_MODELS has entries for all providers."""
        assert Provider.OPENAI in DEFAULT_MODELS
        assert Provider.ANTHROPIC in DEFAULT_MODELS

    def test_get_default_model_openai(self) -> None:
        """Test get_default_model returns correct model for OpenAI."""
        assert get_default_model(Provider.OPENAI) == "gpt-4o"

    def test_get_default_model_anthropic(self) -> None:
        """Test get_default_model returns correct model for Anthropic."""
        assert get_default_model(Provider.ANTHROPIC) == "claude-sonnet-4-5-20250929"

    def test_default_models_are_valid_strings(self) -> None:
        """Test that all default models are non-empty strings."""
        for provider, model in DEFAULT_MODELS.items():
            assert isinstance(model, str), f"Model for {provider} should be a string"
            assert len(model) > 0, f"Model for {provider} should not be empty"


class TestResolveProviderApiKey:
    """Tests for resolve_provider_api_key function."""

    def test_explicit_key_returned(self) -> None:
        """Test that explicit key is returned regardless of env."""
        result = resolve_provider_api_key(Provider.OPENAI, "explicit-key")
        assert result == "explicit-key"

    def test_openai_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test OpenAI API key from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")
        result = resolve_provider_api_key(Provider.OPENAI)
        assert result == "openai-test-key"

    def test_anthropic_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Anthropic API key from environment."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-test-key")
        result = resolve_provider_api_key(Provider.ANTHROPIC)
        assert result == "anthropic-test-key"

    def test_missing_key_returns_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that missing key returns None."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = resolve_provider_api_key(Provider.OPENAI)
        assert result is None


class TestProviderNameType:
    """Tests for ProviderName type."""

    def test_valid_provider_names(self) -> None:
        """Test that ProviderName accepts valid values."""
        # These should not raise type errors
        openai: ProviderName = "openai"
        anthropic: ProviderName = "anthropic"
        assert openai == "openai"
        assert anthropic == "anthropic"


class TestToolEvalDecorator:
    """Tests for tool_eval decorator with provider support."""

    def test_decorator_adds_tool_eval_attribute(self) -> None:
        """Test that decorator adds __tool_eval__ attribute."""

        @tool_eval()
        def my_eval():
            return EvalSuite(name="test", system_message="test")

        assert hasattr(my_eval, "__tool_eval__")
        assert my_eval.__tool_eval__ is True

    @pytest.mark.asyncio
    async def test_wrapper_accepts_provider_parameter(self) -> None:
        """Test that wrapper function accepts provider parameter."""

        # Create a minimal eval suite
        @tool_eval()
        def my_eval():
            suite = EvalSuite(name="test", system_message="test")
            suite.add_tool_definitions([{"name": "test_tool", "description": "test"}])
            suite.add_case(
                name="test case",
                user_message="test",
                expected_tool_calls=[],
            )
            return suite

        # Mock the provider-specific functions to avoid actual API calls
        with patch("arcade_evals.eval._run_with_openai") as mock_openai:
            mock_openai.return_value = {"model": "test", "rubric": EvalRubric(), "cases": []}

            # Call with default provider (openai)
            await my_eval(provider_api_key="test-key", model="gpt-4o")
            mock_openai.assert_called_once()

        with patch("arcade_evals.eval._run_with_anthropic") as mock_anthropic:
            mock_anthropic.return_value = {"model": "test", "rubric": EvalRubric(), "cases": []}

            # Call with anthropic provider
            await my_eval(provider_api_key="test-key", model="claude-3", provider="anthropic")
            mock_anthropic.assert_called_once()


class TestEvalSuiteRun:
    """Tests for EvalSuite.run() with provider support."""

    @pytest.fixture
    def simple_suite(self) -> EvalSuite:
        """Create a simple eval suite for testing."""
        suite = EvalSuite(name="test", system_message="You are a helpful assistant.")
        suite.add_tool_definitions([
            {
                "name": "search",
                "description": "Search for information",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            }
        ])
        suite.add_case(
            name="search test",
            user_message="Search for cats",
            expected_tool_calls=[],
        )
        return suite

    @pytest.mark.asyncio
    async def test_run_with_openai_provider(self, simple_suite: EvalSuite) -> None:
        """Test EvalSuite.run() uses OpenAI format for openai provider."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.tool_calls = None
        mock_client.chat.completions.create.return_value = mock_response

        result = await simple_suite.run(mock_client, "gpt-4o", provider="openai")

        assert result["model"] == "gpt-4o"
        # Verify OpenAI client was called
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        # OpenAI format should have type: "function" wrapper
        assert call_kwargs["tools"][0]["type"] == "function"

    @pytest.mark.asyncio
    async def test_run_with_anthropic_provider(self, simple_suite: EvalSuite) -> None:
        """Test EvalSuite.run() uses Anthropic format for anthropic provider."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = []  # No tool calls
        mock_client.messages.create.return_value = mock_response

        result = await simple_suite.run(mock_client, "claude-3-5-sonnet", provider="anthropic")

        assert result["model"] == "claude-3-5-sonnet"
        # Verify Anthropic client was called
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        # Anthropic format should have input_schema, not parameters wrapped in function
        assert "input_schema" in call_kwargs["tools"][0]
        assert "type" not in call_kwargs["tools"][0]  # No "function" type wrapper


class TestConvertMessagesToAnthropicHelper:
    """Tests for the convert_messages_to_anthropic helper function."""

    def test_empty_messages(self) -> None:
        """Test conversion of empty messages list."""
        result = convert_messages_to_anthropic([])
        assert result == []

    def test_user_messages_pass_through(self) -> None:
        """Test that user messages pass through unchanged."""
        messages = [{"role": "user", "content": "Hello"}]
        result = convert_messages_to_anthropic(messages)
        assert result == [{"role": "user", "content": "Hello"}]

    def test_assistant_messages_pass_through(self) -> None:
        """Test that regular assistant messages pass through unchanged."""
        messages = [{"role": "assistant", "content": "Hi there"}]
        result = convert_messages_to_anthropic(messages)
        assert result == [{"role": "assistant", "content": "Hi there"}]

    def test_system_messages_are_skipped(self) -> None:
        """Test that system messages are skipped."""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]
        result = convert_messages_to_anthropic(messages)
        assert len(result) == 1
        assert result[0]["role"] == "user"

    def test_assistant_with_tool_calls_converted(self) -> None:
        """Test assistant messages with tool_calls are converted to tool_use blocks."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "cats"}'},
                    }
                ],
            }
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert isinstance(result[0]["content"], list)

        tool_use = result[0]["content"][0]
        assert tool_use["type"] == "tool_use"
        assert tool_use["id"] == "call_abc"
        assert tool_use["name"] == "search"
        assert tool_use["input"] == {"q": "cats"}

    def test_tool_messages_converted_to_user_tool_result(self) -> None:
        """Test tool messages are converted to user with tool_result block."""
        messages = [{"role": "tool", "content": "Search results...", "tool_call_id": "call_abc"}]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert isinstance(result[0]["content"], list)

        tool_result = result[0]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "call_abc"
        assert tool_result["content"] == "Search results..."

    def test_multiple_tool_calls_in_single_assistant_message(self) -> None:
        """Test multiple tool_calls in a single assistant message."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "cats"}'},
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {"name": "weather", "arguments": '{"city": "Paris"}'},
                    },
                ],
            }
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        tool_uses = result[0]["content"]
        assert len(tool_uses) == 2
        assert tool_uses[0]["name"] == "search"
        assert tool_uses[1]["name"] == "weather"

    def test_full_conversation_conversion(self) -> None:
        """Test conversion of a full multi-turn conversation with tool use."""
        messages = [
            {"role": "user", "content": "Search for cats"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "cats"}'},
                    }
                ],
            },
            {"role": "tool", "content": "Found 10 results", "tool_call_id": "call_123"},
            {"role": "assistant", "content": "I found 10 results about cats."},
            {"role": "user", "content": "Thanks!"},
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 5
        assert result[0] == {"role": "user", "content": "Search for cats"}
        assert result[1]["role"] == "assistant"
        assert result[1]["content"][0]["type"] == "tool_use"
        assert result[2]["role"] == "user"
        assert result[2]["content"][0]["type"] == "tool_result"
        assert result[3] == {"role": "assistant", "content": "I found 10 results about cats."}
        assert result[4] == {"role": "user", "content": "Thanks!"}

    def test_empty_content_user_message_skipped(self) -> None:
        """Test that user messages with empty content are skipped."""
        messages = [
            {"role": "user", "content": ""},
            {"role": "user", "content": "Hello"},
        ]
        result = convert_messages_to_anthropic(messages)
        assert len(result) == 1
        assert result[0]["content"] == "Hello"

    def test_legacy_function_role_converted(self) -> None:
        """Test that legacy 'function' role is converted to user with tool_result."""
        messages = [{"role": "function", "name": "search", "content": "Search results..."}]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert isinstance(result[0]["content"], list)

        tool_result = result[0]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "search"  # function uses "name"
        assert tool_result["content"] == "Search results..."

    def test_malformed_json_in_tool_calls_arguments(self) -> None:
        """Test that malformed JSON in tool_calls arguments doesn't raise an error."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {
                            "name": "search",
                            "arguments": "invalid json {not valid",  # Malformed JSON
                        },
                    }
                ],
            }
        ]
        # Should not raise, should gracefully handle malformed JSON
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        tool_use = result[0]["content"][0]
        assert tool_use["type"] == "tool_use"
        assert tool_use["name"] == "search"
        assert tool_use["input"] == {}  # Falls back to empty dict

    def test_malformed_tool_calls_missing_function_key(self) -> None:
        """Test that tool_calls with missing 'function' key are skipped gracefully."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "call_1"},  # Missing 'function' key
                    {"id": "call_2", "function": None},  # None function
                    {
                        "id": "call_3",
                        "function": {"name": "valid_tool", "arguments": "{}"},
                    },  # Valid
                ],
            }
        ]
        result = convert_messages_to_anthropic(messages)

        # Should have one message with only the valid tool_use
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        # Only the valid tool should be included
        assert len(result[0]["content"]) == 1
        tool_use = result[0]["content"][0]
        assert tool_use["type"] == "tool_use"
        assert tool_use["name"] == "valid_tool"

    def test_empty_arguments_string_in_tool_calls(self) -> None:
        """Test that empty arguments string is handled correctly."""
        messages = [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "no_args_tool", "arguments": ""},
                    }
                ],
            }
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        tool_use = result[0]["content"][0]
        assert tool_use["input"] == {}

    def test_assistant_with_both_content_and_tool_calls(self) -> None:
        """Test that assistant messages with both content AND tool_calls preserve both.

        This is an edge case where the assistant says something AND calls a tool.
        The text content should be included as a text block before tool_use blocks.
        """
        messages = [
            {
                "role": "assistant",
                "content": "Let me search for that",
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "cats"}'},
                    }
                ],
            }
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        content_blocks = result[0]["content"]

        # Should have both text and tool_use blocks
        assert len(content_blocks) == 2

        # First block should be text
        assert content_blocks[0]["type"] == "text"
        assert content_blocks[0]["text"] == "Let me search for that"

        # Second block should be tool_use
        assert content_blocks[1]["type"] == "tool_use"
        assert content_blocks[1]["name"] == "search"
        assert content_blocks[1]["input"] == {"q": "cats"}

    def test_assistant_with_empty_content_and_tool_calls(self) -> None:
        """Test that empty/None content is not included when tool_calls are present."""
        messages = [
            {
                "role": "assistant",
                "content": "",  # Empty string
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "cats"}'},
                    }
                ],
            }
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        content_blocks = result[0]["content"]

        # Should only have tool_use block, no empty text block
        assert len(content_blocks) == 1
        assert content_blocks[0]["type"] == "tool_use"

    def test_assistant_with_empty_tool_calls_list(self) -> None:
        """Test that empty tool_calls list is handled correctly."""
        messages = [
            {
                "role": "assistant",
                "content": "Hello",
                "tool_calls": [],  # Empty list
            }
        ]
        result = convert_messages_to_anthropic(messages)

        # Should be treated as a regular assistant message
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Hello"  # Simple string, not blocks

    def test_tool_result_added_to_existing_user_message_with_text(self) -> None:
        """Test that tool result is added to existing user message with text content."""
        messages = [
            {"role": "user", "content": "First question"},
            {"role": "tool", "content": "Tool result", "tool_call_id": "call_123"},
        ]
        result = convert_messages_to_anthropic(messages)

        # Should batch into ONE user message with both text and tool_result
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert isinstance(result[0]["content"], list)
        assert len(result[0]["content"]) == 2
        # First block is the original text
        assert result[0]["content"][0]["type"] == "text"
        assert result[0]["content"][0]["text"] == "First question"
        # Second block is the tool result
        assert result[0]["content"][1]["type"] == "tool_result"
        assert result[0]["content"][1]["tool_use_id"] == "call_123"

    def test_three_consecutive_tool_results_all_batched(self) -> None:
        """Test that 3+ consecutive tool results are all batched together."""
        messages = [
            {
                "role": "assistant",
                "tool_calls": [
                    {"id": "c1", "function": {"name": "t1", "arguments": "{}"}},
                    {"id": "c2", "function": {"name": "t2", "arguments": "{}"}},
                    {"id": "c3", "function": {"name": "t3", "arguments": "{}"}},
                ],
            },
            {"role": "tool", "content": "Result 1", "tool_call_id": "c1"},
            {"role": "tool", "content": "Result 2", "tool_call_id": "c2"},
            {"role": "tool", "content": "Result 3", "tool_call_id": "c3"},
        ]
        result = convert_messages_to_anthropic(messages)

        # Should have: assistant with 3 tool_use blocks, then ONE user message with 3 tool_results
        assert len(result) == 2
        assert result[0]["role"] == "assistant"
        assert len(result[0]["content"]) == 3  # 3 tool_use blocks

        assert result[1]["role"] == "user"
        assert len(result[1]["content"]) == 3  # 3 tool_result blocks batched
        assert all(block["type"] == "tool_result" for block in result[1]["content"])

    def test_tool_result_then_user_text_then_tool_result(self) -> None:
        """Test interleaved tool results and user text messages."""
        messages = [
            {
                "role": "assistant",
                "tool_calls": [{"id": "c1", "function": {"name": "t1", "arguments": "{}"}}],
            },
            {"role": "tool", "content": "First result", "tool_call_id": "c1"},
            {"role": "user", "content": "User interrupts"},
            {
                "role": "assistant",
                "tool_calls": [{"id": "c2", "function": {"name": "t2", "arguments": "{}"}}],
            },
            {"role": "tool", "content": "Second result", "tool_call_id": "c2"},
        ]
        result = convert_messages_to_anthropic(messages)

        # Should have: assistant, user (tool_result), user (text), assistant, user (tool_result)
        assert len(result) == 5
        assert result[0]["role"] == "assistant"
        assert result[1]["role"] == "user"
        assert isinstance(result[1]["content"], list)
        assert result[2]["role"] == "user"
        assert result[2]["content"] == "User interrupts"
        assert result[3]["role"] == "assistant"
        assert result[4]["role"] == "user"
        assert isinstance(result[4]["content"], list)

    def test_empty_tool_result_content(self) -> None:
        """Test tool result with empty content string."""
        messages = [
            {"role": "tool", "content": "", "tool_call_id": "call_123"},
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        assert result[0]["role"] == "user"
        tool_result = result[0]["content"][0]
        assert tool_result["content"] == ""

    def test_tool_result_missing_tool_call_id(self) -> None:
        """Test tool result with missing tool_call_id."""
        messages = [
            {"role": "tool", "content": "Result"},  # Missing tool_call_id
        ]
        result = convert_messages_to_anthropic(messages)

        assert len(result) == 1
        tool_result = result[0]["content"][0]
        assert tool_result["tool_use_id"] == ""  # Defaults to empty string

    def test_consecutive_tool_results_batched_into_single_user_message(self) -> None:
        """Test that consecutive tool results are batched into ONE user message.

        This is critical for Anthropic API compatibility - Anthropic requires
        alternating user/assistant roles and rejects consecutive messages of
        the same role. When multiple tool calls are made (parallel tool use),
        their results should be combined into a single user message with
        multiple tool_result content blocks.
        """
        messages = [
            {"role": "user", "content": "Search for cats and get weather in Paris"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "search", "arguments": '{"q": "cats"}'},
                    },
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {"name": "weather", "arguments": '{"city": "Paris"}'},
                    },
                ],
            },
            # Multiple consecutive tool results (common with parallel tool use)
            {"role": "tool", "content": "Search results...", "tool_call_id": "call_1"},
            {"role": "tool", "content": "Weather data...", "tool_call_id": "call_2"},
            {"role": "assistant", "content": "Here are the results..."},
        ]
        result = convert_messages_to_anthropic(messages)

        # Should have: user, assistant (with tool_use), user (with BOTH tool_results), assistant
        assert len(result) == 4
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"  # SINGLE user message with both results
        assert result[3]["role"] == "assistant"

        # The user message should have BOTH tool_result blocks
        tool_results_content = result[2]["content"]
        assert isinstance(tool_results_content, list)
        assert len(tool_results_content) == 2

        # First tool result
        assert tool_results_content[0]["type"] == "tool_result"
        assert tool_results_content[0]["tool_use_id"] == "call_1"
        assert tool_results_content[0]["content"] == "Search results..."

        # Second tool result (batched in same message)
        assert tool_results_content[1]["type"] == "tool_result"
        assert tool_results_content[1]["tool_use_id"] == "call_2"
        assert tool_results_content[1]["content"] == "Weather data..."


class TestAnthropicMessageConversion:
    """Tests for Anthropic message role filtering."""

    @pytest.fixture
    def suite_with_additional_messages(self) -> EvalSuite:
        """Create a suite with various message roles."""
        suite = EvalSuite(name="test", system_message="You are helpful.")
        suite.add_tool_definitions([{"name": "test_tool", "description": "test"}])
        return suite

    @pytest.mark.asyncio
    async def test_converts_tool_role_messages_to_user_tool_result(
        self, suite_with_additional_messages: EvalSuite
    ) -> None:
        """Test that 'tool' role messages are converted to Anthropic user tool_result."""

        # Create a case with mixed message roles including 'tool'
        case = EvalCase(
            name="test",
            system_message="test",
            user_message="test",
            expected_tool_calls=[],
            additional_messages=[
                {"role": "user", "content": "First user message"},
                {"role": "assistant", "content": "First assistant message"},
                {"role": "tool", "content": "Tool result", "tool_call_id": "call_123"},
                {"role": "user", "content": "Second user message"},
            ],
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        await suite_with_additional_messages._run_anthropic(mock_client, "claude-3", case)

        # Check that messages.create was called
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]

        # Verify 'tool' role message was converted to user with tool_result
        messages = call_kwargs["messages"]
        roles = [m["role"] for m in messages]
        assert "tool" not in roles  # No raw 'tool' role
        # Should have: user, assistant, user (tool_result), user, user (the case user_message)
        assert roles == ["user", "assistant", "user", "user", "user"]

        # Find the converted tool_result message
        tool_result_msg = messages[2]
        assert tool_result_msg["role"] == "user"
        assert isinstance(tool_result_msg["content"], list)
        assert tool_result_msg["content"][0]["type"] == "tool_result"
        assert tool_result_msg["content"][0]["tool_use_id"] == "call_123"
        assert tool_result_msg["content"][0]["content"] == "Tool result"

    @pytest.mark.asyncio
    async def test_converts_assistant_tool_calls_to_anthropic_format(
        self, suite_with_additional_messages: EvalSuite
    ) -> None:
        """Test that assistant messages with tool_calls are converted to Anthropic format."""

        # Create a case with OpenAI-style assistant message containing tool_calls
        case = EvalCase(
            name="test",
            system_message="test",
            user_message="test",
            expected_tool_calls=[],
            additional_messages=[
                {"role": "user", "content": "Search for cats"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [  # OpenAI format - should be converted
                        {
                            "id": "call_123",
                            "type": "function",
                            "function": {"name": "search", "arguments": '{"q": "cats"}'},
                        }
                    ],
                },
                {"role": "tool", "content": "Results...", "tool_call_id": "call_123"},
                {"role": "user", "content": "Thanks!"},
            ],
        )

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        await suite_with_additional_messages._run_anthropic(mock_client, "claude-3", case)

        call_kwargs = mock_client.messages.create.call_args[1]
        messages = call_kwargs["messages"]

        # Verify OpenAI format was converted to Anthropic format
        roles = [m["role"] for m in messages]
        # user, assistant (with tool_use), user (with tool_result), user, user (case message)
        assert roles == ["user", "assistant", "user", "user", "user"]

        # Verify no message has raw OpenAI tool_calls
        for msg in messages:
            assert "tool_calls" not in msg

        # Verify assistant message was converted to tool_use block format
        assistant_msg = messages[1]
        assert assistant_msg["role"] == "assistant"
        assert isinstance(assistant_msg["content"], list)
        tool_use_block = assistant_msg["content"][0]
        assert tool_use_block["type"] == "tool_use"
        assert tool_use_block["id"] == "call_123"
        assert tool_use_block["name"] == "search"
        assert tool_use_block["input"] == {"q": "cats"}

        # Verify tool message was converted to user with tool_result
        tool_result_msg = messages[2]
        assert tool_result_msg["role"] == "user"
        assert isinstance(tool_result_msg["content"], list)
        assert tool_result_msg["content"][0]["type"] == "tool_result"
        assert tool_result_msg["content"][0]["tool_use_id"] == "call_123"


class TestAnthropicToolCallExtraction:
    """Tests for extracting tool calls from Anthropic responses."""

    @pytest.fixture
    def suite_with_tool(self) -> EvalSuite:
        """Create a suite with a tool for testing."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {
                "name": "get_weather",
                "description": "Get weather",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string"},
                    },
                    "required": ["city"],
                },
            }
        ])
        suite.add_case(
            name="weather test",
            user_message="What's the weather in Paris?",
            expected_tool_calls=[],
        )
        return suite

    @pytest.mark.asyncio
    async def test_extracts_tool_calls_from_anthropic_response(
        self, suite_with_tool: EvalSuite
    ) -> None:
        """Test that tool calls are correctly extracted from Anthropic response."""
        mock_client = AsyncMock()

        # Create mock tool_use block
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "get_weather"
        mock_tool_block.input = {"city": "Paris"}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_client.messages.create.return_value = mock_response

        result = await suite_with_tool.run(mock_client, "claude-3", provider="anthropic")

        # Check that the tool call was extracted
        case_result = result["cases"][0]
        assert len(case_result["predicted_tool_calls"]) == 1
        assert case_result["predicted_tool_calls"][0]["name"] == "get_weather"
        assert case_result["predicted_tool_calls"][0]["args"] == {"city": "Paris"}


class TestRunWithProviderFunctions:
    """Tests for _run_with_openai and _run_with_anthropic functions."""

    @pytest.fixture
    def minimal_suite(self) -> EvalSuite:
        """Create a minimal suite for testing."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([{"name": "test_tool", "description": "test"}])
        suite.add_case(name="test", user_message="test", expected_tool_calls=[])
        return suite

    @pytest.mark.asyncio
    async def test_run_with_openai_creates_client(self, minimal_suite: EvalSuite) -> None:
        """Test _run_with_openai creates and uses OpenAI client."""
        with patch("arcade_evals.eval.AsyncOpenAI") as mock_openai_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.tool_calls = None
            mock_client.chat.completions.create.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_openai_class.return_value = mock_client

            await _run_with_openai(minimal_suite, "test-key", "gpt-4o")

            mock_openai_class.assert_called_once_with(api_key="test-key")

    @pytest.mark.asyncio
    async def test_run_with_anthropic_creates_client(self, minimal_suite: EvalSuite) -> None:
        """Test _run_with_anthropic creates and uses Anthropic client."""
        with patch("arcade_evals.eval.AsyncAnthropic", create=True) as mock_anthropic_class:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = []
            mock_client.messages.create.return_value = mock_response
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_anthropic_class.return_value = mock_client

            # Patch the import inside the function
            with patch.dict(
                "sys.modules", {"anthropic": MagicMock(AsyncAnthropic=mock_anthropic_class)}
            ):
                # Re-import to get the patched version
                from arcade_evals.eval import _run_with_anthropic as patched_run

                await patched_run(minimal_suite, "test-key", "claude-3")

    @pytest.mark.asyncio
    async def test_run_with_anthropic_raises_on_missing_package(
        self, minimal_suite: EvalSuite
    ) -> None:
        """Test _run_with_anthropic raises ImportError when anthropic not installed."""
        with patch.dict("sys.modules", {"anthropic": None}):
            # Force re-import to trigger ImportError


            # Create a version of the function that will fail to import
            async def failing_run(suite, api_key, model):
                try:
                    raise ImportError("No module named 'anthropic'")
                except ImportError as e:
                    raise ImportError(
                        "The 'anthropic' package is required for Anthropic provider. "
                        "Install it with: pip install anthropic"
                    ) from e

            with pytest.raises(ImportError, match="anthropic.*package is required"):
                await failing_run(minimal_suite, "test-key", "claude-3")


class TestToolCatalogWithAnthropicProvider:
    """Tests for using ToolCatalog-based evals with Anthropic provider."""

    @pytest.mark.asyncio
    async def test_eval_suite_with_tools_works_with_anthropic(self) -> None:
        """Test that EvalSuite with tools works with Anthropic provider.

        This verifies backward compatibility: existing evals can be
        run with --provider anthropic without modification.

        The key is that tools added to EvalSuite (via add_tool_definitions
        or catalog) are automatically converted to Anthropic format when
        provider="anthropic" is used.
        """
        # Create EvalSuite with tools using the convenience method
        suite = EvalSuite(
            name="Test Suite",
            system_message="You are a helpful assistant.",
        )

        # Add tools (simulating what catalog does internally)
        suite.add_tool_definitions([
            {
                "name": "Google.Search",  # Name with dot (like real tools)
                "description": "Search the web",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "max_results": {"type": "integer", "default": 10},
                    },
                    "required": ["query"],
                },
            }
        ])

        # Add a test case
        suite.add_case(
            name="search test",
            user_message="Search for cats",
            expected_tool_calls=[],
        )

        # Mock Anthropic client
        mock_client = AsyncMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "Google_Search"  # Anthropic format (dots -> underscores)
        mock_tool_block.input = {"query": "cats", "max_results": 10}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_client.messages.create.return_value = mock_response

        # Run with Anthropic provider
        result = await suite.run(mock_client, "claude-3", provider="anthropic")

        # Verify the call was made with Anthropic tool format
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]

        # Check tools are in Anthropic format (flat, with input_schema)
        tools = call_kwargs["tools"]
        assert len(tools) == 1
        assert "input_schema" in tools[0]  # Anthropic format
        assert "type" not in tools[0]  # No OpenAI-style "function" wrapper
        assert tools[0]["name"] == "Google_Search"  # Dots converted to underscores

    @pytest.mark.asyncio
    async def test_same_suite_works_with_both_providers(self) -> None:
        """Test that the same EvalSuite works with both OpenAI and Anthropic."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {
                "name": "my_tool",
                "description": "A test tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {"param": {"type": "string"}},
                    "required": ["param"],
                },
            }
        ])
        suite.add_case(name="test", user_message="test", expected_tool_calls=[])

        # Test OpenAI format
        openai_tools = suite._internal_registry.list_tools_for_model("openai")
        assert openai_tools[0]["type"] == "function"
        assert "parameters" in openai_tools[0]["function"]

        # Test Anthropic format
        anthropic_tools = suite._internal_registry.list_tools_for_model("anthropic")
        assert "type" not in anthropic_tools[0]
        assert "input_schema" in anthropic_tools[0]


class TestToolFormatSelection:
    """Tests verifying correct tool format is used for each provider."""

    @pytest.fixture
    def suite_with_tools(self) -> EvalSuite:
        """Create a suite with tools for format testing."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {
                "name": "my_tool",
                "description": "A test tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "param": {"type": "string", "default": "default_value"},
                    },
                    "required": [],
                },
            }
        ])
        return suite

    def test_openai_format_has_function_wrapper(self, suite_with_tools: EvalSuite) -> None:
        """Test that OpenAI format includes type: function wrapper."""
        tools = suite_with_tools._internal_registry.list_tools_for_model("openai")

        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert "function" in tools[0]
        assert tools[0]["function"]["name"] == "my_tool"
        assert "parameters" in tools[0]["function"]

    def test_anthropic_format_is_flat(self, suite_with_tools: EvalSuite) -> None:
        """Test that Anthropic format is flat (no wrapper)."""
        tools = suite_with_tools._internal_registry.list_tools_for_model("anthropic")

        assert len(tools) == 1
        assert "type" not in tools[0]  # No "function" type
        assert "function" not in tools[0]  # No wrapper
        assert tools[0]["name"] == "my_tool"
        assert "input_schema" in tools[0]


class TestNormalizeName:
    """Tests for the normalize_name function."""

    def test_normalizes_underscores_to_dots(self) -> None:
        """Test that underscores are converted to dots."""
        assert normalize_name("Google_Search") == "Google.Search"

    def test_normalizes_hyphens_to_dots(self) -> None:
        """Test that hyphens are converted to dots."""
        assert normalize_name("Google-Search") == "Google.Search"

    def test_preserves_dots(self) -> None:
        """Test that dots are preserved."""
        assert normalize_name("Google.Search") == "Google.Search"

    def test_normalizes_mixed_separators(self) -> None:
        """Test that mixed separators are all converted."""
        assert normalize_name("Google_Gmail-Send.Email") == "Google.Gmail.Send.Email"

    def test_handles_multiple_underscores(self) -> None:
        """Test that multiple underscores are all converted."""
        assert normalize_name("A_B_C_D") == "A.B.C.D"

    def test_handles_no_separators(self) -> None:
        """Test that names without separators are unchanged."""
        assert normalize_name("search") == "search"


class TestCompareToolName:
    """Tests for the compare_tool_name function.

    This is critical for Anthropic support because:
    - Anthropic tool names use underscores (Google_Search)
    - Original tool names may use dots (Google.Search)
    - compare_tool_name must match them regardless of separator style
    """

    def test_matches_dots_vs_underscores(self) -> None:
        """Test that dots and underscores are treated as equivalent."""
        assert compare_tool_name("Google.Search", "Google_Search") is True
        assert compare_tool_name("Google_Search", "Google.Search") is True

    def test_matches_dots_vs_hyphens(self) -> None:
        """Test that dots and hyphens are treated as equivalent."""
        assert compare_tool_name("search-files", "search.files") is True

    def test_matches_identical_names(self) -> None:
        """Test that identical names match."""
        assert compare_tool_name("search", "search") is True
        assert compare_tool_name("Google.Search", "Google.Search") is True

    def test_matches_complex_namespaces(self) -> None:
        """Test matching of complex namespaced names."""
        # Expected (dots) vs Actual (underscores from Anthropic)
        assert compare_tool_name("Google.Gmail.Send.Email", "Google_Gmail_Send_Email") is True

    def test_case_insensitive(self) -> None:
        """Test that comparison is case-insensitive."""
        assert compare_tool_name("Google.Search", "google.search") is True
        assert compare_tool_name("SEARCH", "search") is True

    def test_no_match_different_names(self) -> None:
        """Test that different names don't match."""
        assert compare_tool_name("search", "find") is False
        assert compare_tool_name("Google.Search", "Google.Find") is False

    def test_no_match_different_structure(self) -> None:
        """Test that names with different structure don't match."""
        assert compare_tool_name("Google.Search", "Search") is False
        assert compare_tool_name("A.B.C", "A.B") is False

    def test_anthropic_workflow_scenario(self) -> None:
        """Test the typical Anthropic workflow:
        1. Tool registered as 'Google.Search' (with dot)
        2. Sent to Anthropic as 'Google_Search' (converted)
        3. Anthropic returns 'Google_Search' in response
        4. compare_tool_name must match the expected 'Google.Search'
        """
        expected_name = "Google.Search"  # As defined in ExpectedToolCall
        actual_name = "Google_Search"  # As returned by Anthropic

        assert compare_tool_name(expected_name, actual_name) is True


class TestProcessToolCallsNameResolution:
    """Tests for EvalSuite._process_tool_calls tool name resolution."""

    def test_process_tool_calls_resolves_anthropic_names(self) -> None:
        """Test that Anthropic underscore names are resolved to dot names."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {"name": "Google.Search", "description": "Search", "inputSchema": {}}
        ])

        # Simulate Anthropic returning underscore name
        tool_calls = [("Google_Search", {"query": "test"})]
        processed = suite._process_tool_calls(tool_calls)

        # Should resolve to original dot name
        assert processed[0][0] == "Google.Search"

    def test_process_tool_calls_preserves_original_names(self) -> None:
        """Test that original names are preserved when no resolution needed."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {"name": "simple_tool", "description": "Test", "inputSchema": {}}
        ])

        tool_calls = [("simple_tool", {"arg": "value"})]
        processed = suite._process_tool_calls(tool_calls)

        assert processed[0][0] == "simple_tool"

    def test_process_tool_calls_handles_unknown_tools(self) -> None:
        """Test that unknown tools keep their original names."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {"name": "Google.Search", "description": "Search", "inputSchema": {}}
        ])

        # Tool not in registry
        tool_calls = [("Unknown_Tool", {"arg": "value"})]
        processed = suite._process_tool_calls(tool_calls)

        # Should keep original name since not found
        assert processed[0][0] == "Unknown_Tool"

    def test_process_tool_calls_handles_complex_namespaces(self) -> None:
        """Test resolution of complex namespaced tools."""
        suite = EvalSuite(name="test", system_message="test")
        suite.add_tool_definitions([
            {"name": "Slack.Channel.Create", "description": "Create channel", "inputSchema": {}}
        ])

        # Anthropic format with underscores
        tool_calls = [("Slack_Channel_Create", {"name": "general"})]
        processed = suite._process_tool_calls(tool_calls)

        assert processed[0][0] == "Slack.Channel.Create"


class TestAnthropicEndToEndWorkflow:
    """End-to-end tests for Anthropic evaluation workflow."""

    @pytest.mark.asyncio
    async def test_anthropic_evaluation_with_name_resolution(self) -> None:
        """Test complete evaluation flow with Anthropic name conversion."""
        from arcade_evals import BinaryCritic, ExpectedMCPToolCall

        suite = EvalSuite(name="E2E Test", system_message="You are a helpful assistant")
        suite.add_tool_definitions([
            {
                "name": "Google.Search",
                "description": "Search the web",
                "inputSchema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ])

        suite.add_case(
            name="search test",
            user_message="Search for cats",
            expected_tool_calls=[
                ExpectedMCPToolCall(tool_name="Google.Search", args={"query": "cats"})
            ],
            critics=[BinaryCritic(critic_field="query", weight=1.0)],
        )

        # Mock Anthropic client that returns underscore name
        mock_client = AsyncMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "Google_Search"  # Anthropic returns underscore
        mock_tool_block.input = {"query": "cats"}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await suite.run(mock_client, "claude-3", provider="anthropic")

        # Evaluation should pass - name resolution should work
        assert result["cases"][0]["evaluation"].passed

    @pytest.mark.asyncio
    async def test_anthropic_evaluation_partial_match(self) -> None:
        """Test Anthropic evaluation with partial argument matching."""
        from arcade_evals import BinaryCritic, ExpectedMCPToolCall

        suite = EvalSuite(name="Partial Match", system_message="Helper")
        suite.add_tool_definitions([
            {
                "name": "Weather.GetForecast",
                "description": "Get weather forecast",
                "inputSchema": {
                    "type": "object",
                    "properties": {"location": {"type": "string"}, "days": {"type": "integer"}},
                    "required": ["location"],
                },
            }
        ])

        suite.add_case(
            name="weather test",
            user_message="Weather in Paris",
            expected_tool_calls=[
                ExpectedMCPToolCall(
                    tool_name="Weather.GetForecast", args={"location": "Paris", "days": 5}
                )
            ],
            critics=[
                BinaryCritic(critic_field="location", weight=0.8),
                BinaryCritic(critic_field="days", weight=0.2),
            ],
        )

        mock_client = AsyncMock()
        mock_tool_block = MagicMock()
        mock_tool_block.type = "tool_use"
        mock_tool_block.name = "Weather_GetForecast"
        mock_tool_block.input = {"location": "Paris", "days": 7}  # Wrong days

        mock_response = MagicMock()
        mock_response.content = [mock_tool_block]
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        result = await suite.run(mock_client, "claude-3", provider="anthropic")

        # Should have partial score - tool selection is correct, args partially match
        eval_result = result["cases"][0]["evaluation"]
        # The score includes tool_selection weight (default 0.1) plus critic scores
        # Since location matches and days doesn't, we get partial scoring
        assert eval_result.score > 0.5  # Better than random
        assert eval_result.score < 1.0  # Not perfect
