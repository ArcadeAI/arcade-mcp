"""Tests for Crawl & Index data models in arcade-core.

Covers spec behaviors B1–B9:
  .project/specs/crawl-index-capabilities.md
"""

import pytest
from pydantic import ValidationError

from arcade_core.schema import (
    CrawlResult,
    IndexedObject,
    ObjectReference,
    ToolDefinition,
    ToolInput,
    ToolOutput,
    ToolRequirements,
    ToolkitDefinition,
)

_10_MIB = 10 * 1024 * 1024


@pytest.fixture()
def minimal_tool_definition() -> ToolDefinition:
    """A minimal ToolDefinition with only required fields."""
    return ToolDefinition(
        name="TestTool",
        fully_qualified_name="TestToolkit.TestTool",
        description="A test tool",
        toolkit=ToolkitDefinition(name="TestToolkit"),
        input=ToolInput(parameters=[]),
        output=ToolOutput(),
        requirements=ToolRequirements(),
    )


class TestObjectReferenceMetadataValidation:
    """B1–B2: ObjectReference rejects non-scalar metadata values."""

    @pytest.mark.parametrize(
        "bad_value",
        [
            {"nested": "dict"},
            ["a", "list"],
            {"deep": {"deeper": 1}},
        ],
    )
    def test_nested_metadata_value_raises(self, bad_value: object) -> None:
        """B1: Non-scalar metadata value raises ValidationError at construction."""
        with pytest.raises(ValidationError):
            ObjectReference(id="obj-1", type="document", metadata={"key": bad_value})

    @pytest.mark.parametrize(
        "flat_metadata",
        [
            {"title": "My Doc", "pages": 10, "size": 1.5, "active": True, "tag": None},
            {},
        ],
    )
    def test_flat_metadata_accepted(self, flat_metadata: dict) -> None:
        """B2: Metadata containing only MetadataValue scalars is accepted."""
        obj = ObjectReference(id="obj-1", type="document", metadata=flat_metadata)
        assert obj.metadata == flat_metadata


class TestObjectReferenceIdValidation:
    """B3: ObjectReference rejects empty or whitespace-only IDs."""

    @pytest.mark.parametrize("bad_id", ["", "   ", "\t", "\n"])
    def test_empty_or_whitespace_id_raises(self, bad_id: str) -> None:
        """B3: Empty or whitespace-only id raises ValidationError."""
        with pytest.raises(ValidationError):
            ObjectReference(id=bad_id, type="document")


class TestObjectReferenceUriValidation:
    """B3: ObjectReference rejects empty or whitespace-only URIs."""

    @pytest.mark.parametrize("bad_uri", ["", "   ", "\t"])
    def test_empty_or_whitespace_uri_raises(self, bad_uri: str) -> None:
        """B3: Empty or whitespace-only uri raises ValidationError."""
        with pytest.raises(ValidationError):
            ObjectReference(id="obj-1", type="document", uri=bad_uri)

    def test_none_uri_accepted(self) -> None:
        """URI is optional — None is fine."""
        obj = ObjectReference(id="obj-1", type="document", uri=None)
        assert obj.uri is None

    def test_valid_uri_accepted(self) -> None:
        """A non-empty URI is accepted."""
        obj = ObjectReference(id="obj-1", type="document", uri="https://example.com/doc")
        assert obj.uri == "https://example.com/doc"


class TestCrawlResultDefaults:
    """B4–B5: CrawlResult construction and next_cursor semantics."""

    def test_default_construction(self) -> None:
        """B4: CrawlResult() has empty objects, None next_cursor, empty deleted_ids."""
        result = CrawlResult()
        assert result.objects == []
        assert result.next_cursor is None
        assert result.deleted_ids == []

    def test_next_cursor_none_signals_end_of_pages(self) -> None:
        """B5: next_cursor=None signals no more pages."""
        result = CrawlResult(objects=[], next_cursor=None)
        assert result.next_cursor is None

    def test_empty_string_cursor_normalized_to_none(self) -> None:
        """B5: next_cursor='' is normalized to None at construction."""
        result = CrawlResult(next_cursor="")
        assert result.next_cursor is None


class TestIndexedObjectContentLimit:
    """B6–B7: IndexedObject enforces 10 MiB content limit."""

    def test_content_over_10mib_raises(self) -> None:
        """B6: Content exceeding 10 MiB raises ValidationError."""
        oversized = "x" * (_10_MIB + 1)
        with pytest.raises(ValidationError):
            IndexedObject(id="obj-1", type="document", content=oversized)

    def test_content_exactly_10mib_accepted(self) -> None:
        """B7: Content of exactly 10 MiB is accepted (boundary is exclusive)."""
        exactly_10mib = "x" * _10_MIB
        obj = IndexedObject(id="obj-1", type="document", content=exactly_10mib)
        assert len(obj.content) == _10_MIB

    def test_content_below_limit_accepted(self) -> None:
        """B7: Content well below 10 MiB is accepted."""
        obj = IndexedObject(id="obj-1", type="document", content="hello world")
        assert obj.content == "hello world"


class TestIndexedObjectDefaults:
    """B8: IndexedObject default field values."""

    def test_content_type_defaults_to_text_plain(self) -> None:
        """B8: content_type defaults to 'text/plain' when not provided."""
        obj = IndexedObject(id="obj-1", type="document", content="body text")
        assert obj.content_type == "text/plain"

    def test_content_type_can_be_overridden(self) -> None:
        """B8: content_type is accepted when explicitly set."""
        obj = IndexedObject(
            id="obj-1",
            type="document",
            content="<html></html>",
            content_type="text/html",
        )
        assert obj.content_type == "text/html"


class TestIndexedObjectMetadataValidation:
    """B1: IndexedObject also rejects non-scalar metadata values."""

    @pytest.mark.parametrize(
        "bad_value",
        [
            {"nested": "dict"},
            ["a", "list"],
        ],
    )
    def test_nested_metadata_value_raises(self, bad_value: object) -> None:
        """B1: Non-scalar metadata value on IndexedObject raises ValidationError."""
        with pytest.raises(ValidationError):
            IndexedObject(
                id="obj-1", type="document", content="text", metadata={"key": bad_value}
            )


class TestToolDefinitionRole:
    """B9: ToolDefinition.role defaults to 'tool' and is always serialized."""

    def test_role_defaults_to_tool(self, minimal_tool_definition: ToolDefinition) -> None:
        """B9: role defaults to 'tool', preserving backward compatibility."""
        assert minimal_tool_definition.role == "tool"

    def test_role_always_present_in_serialized_output(
        self, minimal_tool_definition: ToolDefinition
    ) -> None:
        """B9: role field is always present in model_dump() output."""
        dumped = minimal_tool_definition.model_dump()
        assert "role" in dumped
        assert dumped["role"] == "tool"
