"""A model returning malformed tool-call JSON must fail its case, not abort the suite."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_evals import EvalSuite

pytestmark = pytest.mark.evals


def _response(arguments: str) -> MagicMock:
    tool_call = MagicMock()
    tool_call.id = "call_1"
    tool_call.function.name = "search"
    tool_call.function.arguments = arguments
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.tool_calls = [tool_call]
    return response


@pytest.mark.asyncio
async def test_invalid_json_arguments_fail_only_that_case() -> None:
    suite = EvalSuite(name="test", system_message="test")
    suite.add_tool_definitions([
        {
            "name": "search",
            "description": "Search",
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        }
    ])
    suite.add_case(name="bad", user_message="bad", expected_tool_calls=[])
    suite.add_case(name="good", user_message="good", expected_tool_calls=[])

    async def create(**kwargs):
        user = kwargs["messages"][-1]["content"]
        return _response('{"query": "cats"' if user == "bad" else '{"query": "cats"}')

    client = AsyncMock()
    client.chat.completions.create.side_effect = create

    results = await suite.run(client, "gpt-4o", provider="openai")

    by_name = {c["name"]: c for c in results["cases"]}
    assert set(by_name) == {"bad", "good"}
    assert by_name["bad"]["evaluation"].passed is False
    assert "invalid JSON" in by_name["bad"]["evaluation"].failure_reason
    assert by_name["bad"]["predicted_tool_calls"] == []
