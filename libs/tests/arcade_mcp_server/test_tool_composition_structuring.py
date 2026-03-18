"""Tests for Tier 3a/3b LLM extraction in tool composition (Tools.execute)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from pydantic import BaseModel

from arcade_core.errors import ToolResponseExtractionError
from arcade_core.structuring import OnMissing
from arcade_mcp_server.context import Context, _SamplingUnavailableError
from arcade_mcp_server.types import CallToolResult, TextContent


class WeatherResult(BaseModel):
    temperature: float
    city: str
    condition: str


def _raw_result(text: str, structured: dict | None = None) -> CallToolResult:
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structuredContent=structured,
        isError=False,
    )


# ---------------------------------------------------------------------------
# Tier 3a: _extract_via_sampling
# ---------------------------------------------------------------------------


class TestExtractViaSampling:
    @pytest.mark.asyncio
    async def test_raises_unavailable_when_no_session(self, mcp_server):
        ctx = Context(server=mcp_server)
        # No session set — _session is None
        raw = _raw_result("some text")
        with pytest.raises(_SamplingUnavailableError):
            await ctx.tools._extract_via_sampling(WeatherResult, raw, OnMissing.FAIL)

    @pytest.mark.asyncio
    async def test_raises_unavailable_when_client_lacks_capability(self, mcp_server):
        ctx = Context(server=mcp_server)
        mock_session = MagicMock()
        mock_session.create_message = AsyncMock()
        ctx._session = mock_session

        # Patch _check_client_capability to return False
        ctx._check_client_capability = MagicMock(return_value=False)

        raw = _raw_result("some text")
        with pytest.raises(_SamplingUnavailableError):
            await ctx.tools._extract_via_sampling(WeatherResult, raw, OnMissing.FAIL)

    @pytest.mark.asyncio
    async def test_success_parses_json_from_text_content(self, mcp_server):
        ctx = Context(server=mcp_server)
        mock_session = MagicMock()
        response_text = '{"temperature": 22.5, "city": "NYC", "condition": "sunny"}'
        text_content = TextContent(type="text", text=response_text)
        mock_session.create_message = AsyncMock(return_value=MagicMock(content=text_content))
        ctx._session = mock_session
        ctx._check_client_capability = MagicMock(return_value=True)

        raw = _raw_result(json.dumps({"temperature": 22.5, "city": "NYC", "condition": "sunny"}))
        result = await ctx.tools._extract_via_sampling(WeatherResult, raw, OnMissing.FAIL)

        assert result.city == "NYC"
        assert result.temperature == 22.5
        assert result.condition == "sunny"


# ---------------------------------------------------------------------------
# Tier 3b: _extract_via_anthropic
# ---------------------------------------------------------------------------


class TestExtractViaAnthropic:
    @pytest.mark.asyncio
    async def test_raises_immediately_when_no_api_key(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = None

        raw = _raw_result("temperature is 22.5 in NYC, sunny")
        with pytest.raises(ToolResponseExtractionError, match="ANTHROPIC_API_KEY"):
            await ctx.tools._extract_via_anthropic(WeatherResult, raw, OnMissing.FAIL)

    @pytest.mark.asyncio
    async def test_success_with_tool_use_block(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = "test-key-abc"

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {"temperature": 22.5, "city": "NYC", "condition": "sunny"}
        mock_response = MagicMock()
        mock_response.content = [tool_use_block]

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        ctx.tools._anthropic_client = mock_client
        ctx.tools._anthropic_client_key = "test-key-abc"

        raw = _raw_result("temperature is 22.5 in NYC, sunny")
        result = await ctx.tools._extract_via_anthropic(WeatherResult, raw, OnMissing.FAIL)

        assert result.temperature == 22.5
        assert result.city == "NYC"
        assert result.condition == "sunny"

    @pytest.mark.asyncio
    async def test_uses_forced_tool_choice(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = "test-key-abc"

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {"temperature": 0.0, "city": "X", "condition": "Y"}
        mock_response = MagicMock()
        mock_response.content = [tool_use_block]

        mock_create = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.messages.create = mock_create
        ctx.tools._anthropic_client = mock_client
        ctx.tools._anthropic_client_key = "test-key-abc"

        raw = _raw_result("{}")
        await ctx.tools._extract_via_anthropic(WeatherResult, raw, OnMissing.FAIL)

        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["tool_choice"]["type"] == "tool"
        assert "weatherresult" in call_kwargs["tool_choice"]["name"]

    @pytest.mark.asyncio
    async def test_raises_when_no_tool_use_block(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = "test-key-abc"

        text_block = MagicMock()
        text_block.type = "text"
        mock_response = MagicMock()
        mock_response.content = [text_block]

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        ctx.tools._anthropic_client = mock_client
        ctx.tools._anthropic_client_key = "test-key-abc"

        raw = _raw_result("some text")
        with pytest.raises(ToolResponseExtractionError, match="no tool_use block"):
            await ctx.tools._extract_via_anthropic(WeatherResult, raw, OnMissing.FAIL)

    @pytest.mark.asyncio
    async def test_client_is_cached_across_calls(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = "test-key-abc"

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {"temperature": 0.0, "city": "X", "condition": "Y"}
        mock_response = MagicMock()
        mock_response.content = [tool_use_block]

        with patch("anthropic.AsyncAnthropic") as MockClient:
            mock_instance = MagicMock()
            mock_instance.messages.create = AsyncMock(return_value=mock_response)
            MockClient.return_value = mock_instance

            raw = _raw_result("{}")
            await ctx.tools._extract_via_anthropic(WeatherResult, raw, OnMissing.FAIL)
            await ctx.tools._extract_via_anthropic(WeatherResult, raw, OnMissing.FAIL)

            assert MockClient.call_count == 1  # constructed only once

    @pytest.mark.asyncio
    async def test_uses_structured_content_when_available(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = "test-key-abc"

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {"temperature": 5.0, "city": "Oslo", "condition": "cold"}
        mock_response = MagicMock()
        mock_response.content = [tool_use_block]

        mock_create = AsyncMock(return_value=mock_response)
        mock_client = MagicMock()
        mock_client.messages.create = mock_create
        ctx.tools._anthropic_client = mock_client
        ctx.tools._anthropic_client_key = "test-key-abc"

        # structured content should be used over text content
        raw = _raw_result("ignored text", structured={"temp": 5.0, "location": "Oslo"})
        await ctx.tools._extract_via_anthropic(WeatherResult, raw, OnMissing.FAIL)

        call_kwargs = mock_create.call_args.kwargs
        user_content = call_kwargs["messages"][0]["content"]
        # The raw text sent should be the JSON-serialized structured content
        assert '"temp"' in user_content or "5.0" in user_content


# ---------------------------------------------------------------------------
# execute() orchestration
# ---------------------------------------------------------------------------


class TestExecuteOrchestration:
    @pytest.mark.asyncio
    async def test_falls_through_to_anthropic_when_sampling_unavailable(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = "test-key"

        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.input = {"temperature": 5.0, "city": "Oslo", "condition": "cold"}
        mock_response = MagicMock()
        mock_response.content = [tool_use_block]

        # call_raw returns data that fails Tiers 1-2 (unknown keys)
        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result(
                "weather data",
                structured={"temp_c": 5.0, "location": "Oslo", "sky": "cold"},
            )
        )
        # Sampling unavailable
        ctx.tools._extract_via_sampling = AsyncMock(
            side_effect=_SamplingUnavailableError("no sampling")
        )
        # Anthropic available
        ctx.tools._anthropic_client = MagicMock()
        ctx.tools._anthropic_client.messages.create = AsyncMock(return_value=mock_response)
        ctx.tools._anthropic_client_key = "test-key"

        result = await ctx.tools.execute(WeatherResult, "some_tool", {})
        assert result.city == "Oslo"

    @pytest.mark.asyncio
    async def test_does_not_try_anthropic_on_non_capability_sampling_error(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = "test-key"

        # Tier 1-2 succeeds directly
        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result(
                "weather",
                structured={"temperature": 22.5, "city": "NYC", "condition": "sunny"},
            )
        )

        anthropic_mock = AsyncMock()
        ctx.tools._extract_via_anthropic = anthropic_mock

        result = await ctx.tools.execute(WeatherResult, "some_tool", {})
        assert result.city == "NYC"
        anthropic_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_partial_tier12_when_all_llm_unavailable_allow_null(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = None  # Anthropic unavailable

        # Tier 1-2 returns partial match (city present, others missing → None with ALLOW_NULL)
        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result("city data", structured={"city": "Oslo"})
        )
        ctx.tools._extract_via_sampling = AsyncMock(
            side_effect=_SamplingUnavailableError("no sampling")
        )

        result = await ctx.tools.execute(
            WeatherResult, "some_tool", {}, options={"on_missing": OnMissing.ALLOW_NULL}
        )
        assert result.city == "Oslo"
        assert result.temperature is None  # type: ignore[comparison-overlap]
        assert result.condition is None  # type: ignore[comparison-overlap]

    @pytest.mark.asyncio
    async def test_raises_when_all_llm_unavailable_on_missing_fail(self, mcp_server):
        ctx = Context(server=mcp_server)
        ctx.server.settings.anthropic.api_key = None

        ctx.tools.call_raw = AsyncMock(
            return_value=_raw_result("bad data", structured={"unknown_key": "value"})
        )
        ctx.tools._extract_via_sampling = AsyncMock(
            side_effect=_SamplingUnavailableError("no sampling")
        )

        with pytest.raises(ToolResponseExtractionError):
            await ctx.tools.execute(WeatherResult, "some_tool", {})
