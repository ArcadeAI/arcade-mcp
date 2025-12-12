"""Tests for Prompt Manager implementation."""

import asyncio
from unittest.mock import Mock

import pytest
from arcade_mcp_server.context import Context
from arcade_mcp_server.exceptions import NotFoundError, PromptError
from arcade_mcp_server.managers.prompt import PromptManager
from arcade_mcp_server.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
)


class TestPromptManager:
    """Test PromptManager class."""

    @pytest.fixture
    def prompt_manager(self):
        """Create a prompt manager instance."""
        return PromptManager()

    @pytest.fixture
    def sample_prompt(self):
        """Create a sample prompt."""
        return Prompt(
            name="greeting",
            description="A greeting prompt",
            arguments=[
                PromptArgument(name="name", description="The name to greet", required=True),
                PromptArgument(
                    name="formal", description="Whether to use formal greeting", required=False
                ),
            ],
        )

    @pytest.fixture
    def prompt_function(self):
        """Create a prompt function (legacy signature without context)."""

        async def greeting_prompt(args: dict[str, str]) -> list[PromptMessage]:
            name = args.get("name", "")
            formal_arg = args.get("formal", "false")
            formal = str(formal_arg).lower() == "true"

            if formal:
                text = f"Good day, {name}. How may I assist you?"
            else:
                text = f"Hey {name}! What's up?"

            return [PromptMessage(role="assistant", content={"type": "text", "text": text})]

        return greeting_prompt

    @pytest.fixture
    def prompt_function_with_context(self):
        """Create a prompt function with context parameter (new signature)."""

        async def greeting_prompt_with_context(
            context: Context, args: dict[str, str]
        ) -> list[PromptMessage]:
            name = args.get("name", "")
            formal_arg = args.get("formal", "false")
            formal = str(formal_arg).lower() == "true"

            # Access context (e.g., for logging)
            if hasattr(context, "log"):
                await context.log.info(f"Generating greeting for {name}")

            if formal:
                text = f"Good day, {name}. How may I assist you?"
            else:
                text = f"Hey {name}! What's up?"

            return [PromptMessage(role="assistant", content={"type": "text", "text": text})]

        return greeting_prompt_with_context

    @pytest.fixture
    def mock_context(self):
        """Create a mock context."""
        mock_server = Mock()
        context = Context(mock_server)
        # Mock the log interface with async methods
        mock_log = Mock()
        
        async def async_info(*args, **kwargs):
            pass
        
        mock_log.info = async_info
        context._log = mock_log
        return context

    def test_manager_initialization(self):
        """Test prompt manager initialization."""
        manager = PromptManager()
        assert isinstance(manager, PromptManager)

    @pytest.mark.asyncio
    async def test_manager_lifecycle(self, prompt_manager):
        """Passive manager has no explicit lifecycle; ensure methods work."""
        # Initially empty
        prompts = await prompt_manager.list_prompts()
        assert prompts == []

    @pytest.mark.asyncio
    async def test_add_prompt(self, prompt_manager, sample_prompt, prompt_function):
        """Test adding prompts."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function)

        prompts = await prompt_manager.list_prompts()
        assert len(prompts) == 1
        assert prompts[0].name == sample_prompt.name
        assert len(prompts[0].arguments) == 2

    @pytest.mark.asyncio
    async def test_remove_prompt(self, prompt_manager, sample_prompt, prompt_function):
        """Test removing prompts."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function)
        removed = await prompt_manager.remove_prompt(sample_prompt.name)
        assert removed.name == sample_prompt.name

        prompts = await prompt_manager.list_prompts()
        assert len(prompts) == 0

    @pytest.mark.asyncio
    async def test_get_prompt(self, prompt_manager, sample_prompt, prompt_function):
        """Test getting and executing prompts."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function)

        result = await prompt_manager.get_prompt("greeting", {"name": "Alice", "formal": True})

        assert isinstance(result, GetPromptResult)
        assert len(result.messages) == 1
        assert result.messages[0].role == "assistant"
        assert "Good day, Alice" in result.messages[0].content["text"]

    @pytest.mark.asyncio
    async def test_get_prompt_default_args(self, prompt_manager, sample_prompt, prompt_function):
        """Test getting prompt with default arguments."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function)

        result = await prompt_manager.get_prompt("greeting", {"name": "Bob"})
        assert "Hey Bob!" in result.messages[0].content["text"]

    @pytest.mark.asyncio
    async def test_get_prompt_missing_required_args(
        self, prompt_manager, sample_prompt, prompt_function
    ):
        """Test getting prompt without required arguments."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function)

        with pytest.raises(PromptError):
            await prompt_manager.get_prompt("greeting", {"formal": True})

    @pytest.mark.asyncio
    async def test_get_nonexistent_prompt(self, prompt_manager):
        """Test getting non-existent prompt."""
        with pytest.raises(NotFoundError):
            await prompt_manager.get_prompt("nonexistent", {})

    @pytest.mark.asyncio
    async def test_prompt_with_multiple_messages(self, prompt_manager):
        """Test prompt that returns multiple messages."""
        prompt = Prompt(name="conversation", description="A conversation prompt")

        async def conversation_prompt(args: dict[str, str]) -> list[PromptMessage]:
            return [
                PromptMessage(role="user", content={"type": "text", "text": "Hello!"}),
                PromptMessage(role="assistant", content={"type": "text", "text": "Hi there!"}),
                PromptMessage(role="user", content={"type": "text", "text": "How are you?"}),
                PromptMessage(
                    role="assistant", content={"type": "text", "text": "I'm doing well, thanks!"}
                ),
            ]

        await prompt_manager.add_prompt(prompt, conversation_prompt)

        result = await prompt_manager.get_prompt("conversation", {})

        assert len(result.messages) == 4
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_prompt_with_image_content(self, prompt_manager):
        """Test prompt with image content."""
        prompt = Prompt(
            name="image_analysis",
            description="Analyze an image",
            arguments=[PromptArgument(name="image_url", required=True)],
        )

        async def image_prompt(args: dict[str, str]) -> list[PromptMessage]:
            image_url = args.get("image_url", "")
            return [
                PromptMessage(
                    role="user",
                    content={"type": "image", "data": image_url, "mimeType": "image/jpeg"},
                ),
                PromptMessage(
                    role="user", content={"type": "text", "text": "Please analyze this image"}
                ),
            ]

        await prompt_manager.add_prompt(prompt, image_prompt)

        result = await prompt_manager.get_prompt(
            "image_analysis", {"image_url": "http://example.com/image.jpg"}
        )

        assert len(result.messages) == 2
        assert result.messages[0].content["type"] == "image"
        assert result.messages[1].content["type"] == "text"

    @pytest.mark.asyncio
    async def test_prompt_with_embedded_resource(self, prompt_manager):
        """Test prompt with embedded resources."""
        prompt = Prompt(name="with_resource", description="Prompt with embedded resource")

        async def resource_prompt(args: dict[str, str]) -> list[PromptMessage]:
            return [
                PromptMessage(
                    role="user",
                    content={
                        "type": "resource",
                        "resource": {"uri": "file:///data.txt", "text": "Sample data"},
                    },
                )
            ]

        await prompt_manager.add_prompt(prompt, resource_prompt)

        result = await prompt_manager.get_prompt("with_resource", {})

        assert result.messages[0].content["type"] == "resource"
        assert result.messages[0].content["resource"]["uri"] == "file:///data.txt"

    @pytest.mark.asyncio
    async def test_concurrent_prompt_operations(self, prompt_manager):
        """Test concurrent prompt operations."""
        prompts = []
        for i in range(10):
            prompt = Prompt(name=f"prompt_{i}", description=f"Prompt {i}")

            async def func(args: dict[str, str], idx=i):
                return [
                    PromptMessage(
                        role="assistant", content={"type": "text", "text": f"Response {idx}"}
                    )
                ]

            prompts.append((prompt, func))

        tasks = [prompt_manager.add_prompt(p, f) for p, f in prompts]
        await asyncio.gather(*tasks)

        listed = await prompt_manager.list_prompts()
        assert len(listed) == 10

    @pytest.mark.asyncio
    async def test_list_prompts_initial(self, prompt_manager):
        """Passive manager lists prompts initially as empty."""
        prompts = await prompt_manager.list_prompts()
        assert prompts == []

    @pytest.mark.asyncio
    async def test_prompt_error_handling(self):
        """Test error handling in prompt functions."""
        manager = PromptManager()
        prompt = Prompt(name="error_prompt", description="Prompt that errors")

        async def error_prompt(args: dict[str, str]):
            raise RuntimeError("Prompt execution failed")

        await manager.add_prompt(prompt, error_prompt)

        with pytest.raises(PromptError):
            await manager.get_prompt("error_prompt", {})

    @pytest.mark.asyncio
    async def test_prompt_with_context_parameter(
        self, prompt_manager, sample_prompt, prompt_function_with_context, mock_context
    ):
        """Test prompt with new context parameter signature."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function_with_context)

        result = await prompt_manager.get_prompt(
            "greeting", {"name": "Alice", "formal": "true"}, mock_context
        )

        assert isinstance(result, GetPromptResult)
        assert len(result.messages) == 1
        assert result.messages[0].role == "assistant"
        assert "Good day, Alice" in result.messages[0].content["text"]

    @pytest.mark.asyncio
    async def test_prompt_with_context_logging(
        self, prompt_manager, sample_prompt, prompt_function_with_context, mock_context
    ):
        """Test that prompt with context can use logging."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function_with_context)

        await prompt_manager.get_prompt("greeting", {"name": "Bob"}, mock_context)

        # Verify logging was called (if mock was set up properly)
        # This would require a more sophisticated mock setup

    @pytest.mark.asyncio
    async def test_prompt_context_required_but_not_provided(
        self, prompt_manager, sample_prompt, prompt_function_with_context
    ):
        """Test that error is raised when context-requiring prompt doesn't get context."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function_with_context)

        with pytest.raises(PromptError, match="Handler requires context"):
            await prompt_manager.get_prompt("greeting", {"name": "Alice"}, None)

    @pytest.mark.asyncio
    async def test_backward_compatibility_legacy_signature(
        self, prompt_manager, sample_prompt, prompt_function
    ):
        """Test backward compatibility with legacy signature (no context)."""
        await prompt_manager.add_prompt(sample_prompt, prompt_function)

        # Should work without context
        result = await prompt_manager.get_prompt("greeting", {"name": "Charlie"}, None)

        assert isinstance(result, GetPromptResult)
        assert len(result.messages) == 1
        assert "Hey Charlie!" in result.messages[0].content["text"]

    @pytest.mark.asyncio
    async def test_mixed_signatures(
        self, prompt_manager, prompt_function, prompt_function_with_context, mock_context
    ):
        """Test that both signatures can coexist."""
        prompt1 = Prompt(name="legacy", description="Legacy prompt")
        prompt2 = Prompt(name="new", description="New prompt with context")

        await prompt_manager.add_prompt(prompt1, prompt_function)
        await prompt_manager.add_prompt(prompt2, prompt_function_with_context)

        # Legacy prompt works without context
        result1 = await prompt_manager.get_prompt(
            "legacy", {"name": "Dave", "formal": "false"}, None
        )
        assert "Hey Dave!" in result1.messages[0].content["text"]

        # New prompt works with context
        result2 = await prompt_manager.get_prompt(
            "new", {"name": "Eve", "formal": "true"}, mock_context
        )
        assert "Good day, Eve" in result2.messages[0].content["text"]

    @pytest.mark.asyncio
    async def test_sync_prompt_function_with_context(self, prompt_manager, mock_context):
        """Test synchronous prompt function with context parameter."""
        prompt = Prompt(name="sync_prompt", description="Sync prompt with context")

        def sync_prompt(context: Context, args: dict[str, str]) -> list[PromptMessage]:
            name = args.get("name", "User")
            return [
                PromptMessage(role="user", content={"type": "text", "text": f"Hello {name}!"})
            ]

        await prompt_manager.add_prompt(prompt, sync_prompt)

        result = await prompt_manager.get_prompt("sync_prompt", {"name": "Frank"}, mock_context)

        assert isinstance(result, GetPromptResult)
        assert len(result.messages) == 1
        assert "Hello Frank!" in result.messages[0].content["text"]

    @pytest.mark.asyncio
    async def test_sync_prompt_function_without_context(self, prompt_manager):
        """Test synchronous prompt function without context (legacy)."""
        prompt = Prompt(name="sync_legacy", description="Sync legacy prompt")

        def sync_legacy_prompt(args: dict[str, str]) -> list[PromptMessage]:
            name = args.get("name", "User")
            return [
                PromptMessage(role="user", content={"type": "text", "text": f"Hi {name}!"})
            ]

        await prompt_manager.add_prompt(prompt, sync_legacy_prompt)

        result = await prompt_manager.get_prompt("sync_legacy", {"name": "Grace"}, None)

        assert isinstance(result, GetPromptResult)
        assert len(result.messages) == 1
        assert "Hi Grace!" in result.messages[0].content["text"]
