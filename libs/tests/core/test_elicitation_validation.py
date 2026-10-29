import pytest
from arcade_core.elicitation import Elicitation, InputRequired
from arcade_core.schema import ToolCallProtocol
from arcade_mcp_server.context import UI
from arcade_mcp_server.exceptions import UnsupportedSchemaDialectError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "schema",
    [
        {"type": "array"},
        {"type": "object", "properties": {"nested": {"type": "object"}}},
        {"type": "object", "$schema": "https://example.com/dialect"},
        {
            "type": "object",
            "properties": {"values": {"type": "array", "items": {"type": "string"}}},
        },
    ],
)
async def test_modern_and_legacy_authoring_reject_same_invalid_schemas(schema):
    with pytest.raises(ValueError):
        UI._validate_elicitation_schema(None, schema)
    flow = Elicitation(
        ToolCallProtocol(version="2026-07-28", capabilities={"elicitation": {}}), "s" * 32, {}
    )
    with pytest.raises(ValueError):
        await flow.elicit("Confirm", schema=schema)


def test_legacy_dialect_error_retains_public_exception_type():
    with pytest.raises(UnsupportedSchemaDialectError):
        UI._validate_elicitation_schema(None, {"type": "object", "$schema": "unsupported"})


@pytest.mark.asyncio
async def test_shared_key_resumes_on_another_instance_without_coercing_content():
    protocol = ToolCallProtocol(version="2026-07-28", capabilities={"elicitation": {}})
    with pytest.raises(InputRequired) as first:
        await Elicitation(protocol, "s" * 32, {}).elicit("Confirm")
    result = first.value.result
    protocol.request_state = result["requestState"]
    protocol.input_responses = {
        "1": {"action": "accept", "content": {"unexpected": [1, 2]}, "x-extra": "keep"}
    }
    answer = await Elicitation(protocol, "s" * 32, {}).elicit("Confirm")
    assert answer.model_dump(exclude_none=True) == protocol.input_responses["1"]
    with pytest.raises(ValueError, match="Invalid or expired"):
        Elicitation(protocol, "t" * 32, {})
