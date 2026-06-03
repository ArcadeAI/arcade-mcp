"""Cross-converter guard: one tool, three schema dialects, one shared invariant.

Arcade renders a tool's `ValueSchema` into JSON Schema in three independent places that have
historically drifted into the same class of bug (incompletely-expanded nested objects):

- ``to_openai``      -> OpenAI strict dialect (every object closed; ALL keys required; optionals nullable)
- ``to_anthropic``   -> standard dialect (only actually-required keys; no ``additionalProperties``)
- ``create_mcp_tool``-> MCP inputSchema (standard, but closed objects carry ``additionalProperties: false``)

This builds a single realistic tool exercising a Pydantic-model param, a ``list[TypedDict]`` with a
nested TypedDict, and optional/nullable fields, then asserts each dialect's invariant end-to-end
(catalog -> converter). If any path regresses to bare ``{"type": "object"}`` items or forgets
``additionalProperties`` on closed objects, exactly one of these tests fails.
"""

from typing import Annotated, Optional

from arcade_core.catalog import ToolCatalog
from arcade_core.converters.anthropic import to_anthropic
from arcade_core.converters.openai import to_openai
from arcade_mcp_server.convert import create_mcp_tool
from arcade_tdk import tool
from pydantic import BaseModel
from typing_extensions import TypedDict


class Recipient(BaseModel):
    """An email recipient."""

    email: str
    name: Optional[str] = None


class FileMeta(TypedDict):
    """Metadata for an attachment."""

    key: str
    label: str


class AttachmentTD(TypedDict):
    """A file attachment with nested metadata."""

    source: str
    meta: FileMeta


@tool(desc="Send an email with structured params")
def send_email(
    recipient: Annotated[Recipient, "Who to send to"],
    attachments: Annotated[list[AttachmentTD], "Files to attach"],
    subject: Annotated[Optional[str], "Subject line"] = None,
) -> str:
    return "sent"


def _materialize():
    catalog = ToolCatalog()
    catalog.add_tool(send_email, "consistency")
    return next(iter(catalog))


def _assert_openai_strict(schema: dict) -> None:
    """Recursively: every object subschema is closed and lists ALL its properties as required."""
    types = schema["type"] if isinstance(schema.get("type"), list) else [schema.get("type")]
    if "object" in types and "properties" in schema:
        assert schema.get("additionalProperties") is False, schema
        assert set(schema.get("required", [])) == set(schema["properties"]), schema
        for sub in schema["properties"].values():
            _assert_openai_strict(sub)
    if "array" in types and isinstance(schema.get("items"), dict):
        _assert_openai_strict(schema["items"])


def test_openai_strict_invariant_holds_end_to_end():
    params = to_openai(_materialize())["function"]["parameters"]
    _assert_openai_strict(params)

    recipient = params["properties"]["recipient"]
    assert recipient["additionalProperties"] is False
    assert set(recipient["required"]) == {"email", "name"}  # strict lists every key
    assert recipient["properties"]["name"]["type"] == ["string", "null"]  # optional -> nullable

    items = params["properties"]["attachments"]["items"]
    assert items["additionalProperties"] is False
    assert set(items["required"]) == {"source", "meta"}
    assert items["properties"]["meta"]["additionalProperties"] is False


def test_anthropic_standard_invariant_holds_end_to_end():
    schema = to_anthropic(_materialize())["input_schema"]

    recipient = schema["properties"]["recipient"]
    assert recipient["properties"].keys() == {"email", "name"}
    assert recipient["required"] == ["email"]  # only the actually-required field
    assert "additionalProperties" not in recipient

    items = schema["properties"]["attachments"]["items"]
    assert items["required"] == ["meta", "source"]  # sorted required keys
    assert items["properties"]["meta"]["required"] == ["key", "label"]
    assert "additionalProperties" not in items


def test_mcp_inputschema_closes_known_objects_end_to_end():
    schema = create_mcp_tool(_materialize()).inputSchema

    recipient = schema["properties"]["recipient"]
    assert recipient["additionalProperties"] is False
    assert recipient["required"] == ["email"]
    assert recipient["properties"]["name"]["type"] == ["string", "null"]  # nullable optional

    items = schema["properties"]["attachments"]["items"]
    assert items["additionalProperties"] is False
    assert items["required"] == ["meta", "source"]
    assert items["properties"]["meta"]["additionalProperties"] is False
