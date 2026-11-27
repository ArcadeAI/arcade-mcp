import json
from typing import Annotated

import pytest
from arcade_core import ToolResult
from arcade_core.catalog import ToolCatalog, create_output_definition, determine_output_model
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolContext
from arcade_tdk import tool
from typing_extensions import TypedDict

IMAGE_BLOCK = {"type": "image", "data": "aGVsbG8=", "mimeType": "image/png"}


class FileDetails(TypedDict):
    """A file's details."""

    name: str
    size: int


@tool
def file_with_picture() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a file's details and its picture."""
    return ToolResult(FileDetails(name="cat.png", size=5), content=[IMAGE_BLOCK])


@tool
def file_details() -> Annotated[FileDetails, "The file"]:
    """Return a file's details."""
    return FileDetails(name="cat.png", size=5)


@tool
def bad_value_with_picture() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a value that does not match the output schema."""
    return ToolResult({"name": "cat.png"}, content=[IMAGE_BLOCK])  # type: ignore[arg-type]


@tool
def file_without_content() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a file's details with no content blocks."""
    return ToolResult(FileDetails(name="cat.png", size=5))


@tool
def file_with_raw_bytes() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return raw bytes instead of a content block."""
    return ToolResult(FileDetails(name="cat.png", size=5), content=[b"\x89PNG"])


@tool
def maybe_file() -> Annotated[ToolResult[FileDetails] | None, "The file, if any"]:
    """Return a file's details and its picture, or nothing."""
    return ToolResult(FileDetails(name="cat.png", size=5), content=[IMAGE_BLOCK])


catalog = ToolCatalog()
for func in (
    maybe_file,
    file_with_picture,
    file_details,
    bad_value_with_picture,
    file_without_content,
    file_with_raw_bytes,
):
    catalog.add_tool(func, "Files")


async def _run(func):
    materialized = catalog.get_tool(catalog.find_tool_by_func(func).get_fully_qualified_name())
    return await ToolExecutor.run(
        func=materialized.tool,
        definition=materialized.definition,
        input_model=materialized.input_model,
        output_model=materialized.output_model,
        context=ToolContext(),
    )


@pytest.mark.asyncio
async def test_tool_result_returns_value_and_external_content():
    output = await _run(file_with_picture)

    value = {"name": "cat.png", "size": 5}
    assert output.error is None
    assert output.value == value
    assert output.external == {
        "content": [IMAGE_BLOCK, {"type": "text", "text": json.dumps(value, ensure_ascii=False)}],
        "structuredContent": value,
        "isError": False,
    }


@pytest.mark.asyncio
async def test_tool_result_value_is_validated_against_output_model():
    output = await _run(bad_value_with_picture)

    assert output.error is not None
    assert output.external is None


@pytest.mark.asyncio
async def test_plain_return_has_no_external():
    output = await _run(file_details)

    assert output.value == {"name": "cat.png", "size": 5}
    assert output.external is None


def test_tool_result_output_definition_matches_inner_type():
    assert create_output_definition(file_with_picture) == create_output_definition(file_details)


def test_tool_result_output_model_schema_matches_inner_type():
    wrapped = determine_output_model(file_with_picture).model_json_schema()
    plain = determine_output_model(file_details).model_json_schema()

    assert json.dumps(wrapped).replace("FileWithPicture", "X") == json.dumps(plain).replace(
        "FileDetails", "X"
    )


@pytest.mark.asyncio
async def test_tool_result_without_content_returns_what_a_plain_return_does():
    assert await _run(file_without_content) == await _run(file_details)


@pytest.mark.asyncio
async def test_content_that_is_not_a_block_is_an_output_error():
    output = await _run(file_with_raw_bytes)

    assert output.error is not None
    assert "TOOL_RUNTIME_BAD_OUTPUT_VALUE" in output.error.message
    assert output.external is None


@pytest.mark.asyncio
async def test_optional_tool_result_unwraps_to_its_value():
    definition = catalog.find_tool_by_func(maybe_file)

    assert definition.output.value_schema.val_type == "json"
    output = await _run(maybe_file)
    assert output.value == {"name": "cat.png", "size": 5}
    assert output.external["content"][0] == IMAGE_BLOCK


@tool
def file_with_bad_text_block() -> Annotated[ToolResult[FileDetails], "The file"]:
    """Return a text block whose _meta is not an object."""
    return ToolResult(
        FileDetails(name="cat.png", size=5),
        content=[{"type": "text", "text": "SECRET_BLOCK_TEXT", "_meta": "SECRET_META"}],
    )


catalog.add_tool(file_with_bad_text_block, "Files")


@pytest.mark.asyncio
async def test_rejected_content_is_not_echoed_in_the_error():
    output = await _run(file_with_bad_text_block)

    assert output.error is not None
    assert "TOOL_RUNTIME_BAD_OUTPUT_VALUE" in output.error.message
    assert output.error.stacktrace is None
    for value in ("SECRET_BLOCK_TEXT", "SECRET_META"):
        assert value not in output.model_dump_json()
