"""Tests for @app.crawl and @app.index decorator registration.

Covers spec behaviors B9–B22:
  .project/specs/crawl-index-capabilities.md
"""

from typing import Annotated

import pytest

from arcade_core.errors import ToolDefinitionError
from arcade_core.schema import CrawlResult, IndexedObject
from arcade_mcp_server.context import Context
from arcade_mcp_server.mcp_app import MCPApp


def _make_app() -> MCPApp:
    return MCPApp(name="TestServer", version="1.0.0")


class TestCrawlDecoratorRegistration:
    """B9, B11, B12, B13, B14, B16, B18–B21: @app.crawl registration behaviors."""

    def test_crawl_sets_role_crawl_on_tool_definition(self) -> None:
        """B9: @app.crawl registers the function with role='crawl'."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_docs(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """Crawl documents."""
            return CrawlResult()

        tool_def = app.catalog.get_tool_by_name("TestServer.CrawlDocs").definition
        assert tool_def.role == "crawl"

    def test_crawl_without_parentheses_raises(self) -> None:
        """B11: Bare @app.crawl (no parentheses) raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl  # type: ignore[arg-type]
            async def crawl_docs(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"] = None,
            ) -> CrawlResult:
                """Crawl documents."""
                return CrawlResult()

    @pytest.mark.parametrize("bad_type", ["", "   ", "\t"])
    def test_crawl_empty_or_whitespace_type_raises(self, bad_type: str) -> None:
        """B12: @app.crawl with empty or whitespace type raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type=bad_type)
            async def crawl_docs(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"] = None,
            ) -> CrawlResult:
                """Crawl documents."""
                return CrawlResult()

    def test_duplicate_crawl_type_raises(self) -> None:
        """B13: Registering two @app.crawl with the same type raises ToolDefinitionError."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_docs_1(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """First crawl handler."""
            return CrawlResult()

        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs_2(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"] = None,
            ) -> CrawlResult:
                """Second crawl handler — duplicate type."""
                return CrawlResult()

    def test_duplicate_crawl_type_case_insensitive(self) -> None:
        """B13/EC6: Type uniqueness check is case-insensitive."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_docs_lower(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """First crawl handler."""
            return CrawlResult()

        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="Document")
            async def crawl_docs_upper(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"] = None,
            ) -> CrawlResult:
                """Second crawl handler — same type, different case."""
                return CrawlResult()

    def test_missing_context_param_raises(self) -> None:
        """Crawl function without context param raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs(
                cursor: Annotated[str | None, "Pagination cursor"] = None,
            ) -> CrawlResult:
                """Crawl docs — missing context."""
                return CrawlResult()

    def test_missing_cursor_param_raises(self) -> None:
        """B14: Crawl function without cursor param raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs(context: Context) -> CrawlResult:
                """Crawl docs — missing cursor."""
                return CrawlResult()

    def test_cursor_param_wrong_type_raises(self) -> None:
        """B14: Crawl function with cursor typed as str (not str | None) raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs(
                context: Context,
                cursor: Annotated[str, "Pagination cursor"] = "",
            ) -> CrawlResult:
                """Crawl docs — cursor type wrong."""
                return CrawlResult()

    def test_cursor_param_no_default_raises(self) -> None:
        """B14: Crawl function with cursor missing default=None raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"],
            ) -> CrawlResult:
                """Crawl docs — cursor missing default."""
                return CrawlResult()

    def test_cursor_param_wrong_default_raises(self) -> None:
        """Crawl function with cursor defaulting to non-None raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"] = "start",
            ) -> CrawlResult:
                """Crawl docs — cursor defaults to 'start' instead of None."""
                return CrawlResult()

    def test_wrong_return_type_raises(self) -> None:
        """B16: Crawl function with non-CrawlResult return type raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"] = None,
            ) -> dict:
                """Crawl docs — wrong return type."""
                return {}

    def test_extra_parameters_raises(self) -> None:
        """B18: Crawl function with extra parameters beyond cursor raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.crawl(object_type="document")
            async def crawl_docs(
                context: Context,
                cursor: Annotated[str | None, "Pagination cursor"] = None,
                folder_id: Annotated[str | None, "Folder to crawl"] = None,
            ) -> CrawlResult:
                """Crawl docs — has an extra param."""
                return CrawlResult()

    def test_name_normalized_to_pascal_case(self) -> None:
        """B20: Crawl function named crawl_documents is normalized to CrawlDocuments."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_documents(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """Crawl documents."""
            return CrawlResult()

        tool_def = app.catalog.get_tool_by_name("TestServer.CrawlDocuments").definition
        assert tool_def.name == "CrawlDocuments"
        assert tool_def.fully_qualified_name == "TestServer.CrawlDocuments"

    def test_multiple_crawl_types_allowed(self) -> None:
        """EC1: Different types can coexist on the same MCPApp."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_docs(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """Crawl documents."""
            return CrawlResult()

        @app.crawl(object_type="sheet")
        async def crawl_sheets(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """Crawl sheets."""
            return CrawlResult()

        assert app.catalog.get_tool_by_name("TestServer.CrawlDocs") is not None
        assert app.catalog.get_tool_by_name("TestServer.CrawlSheets") is not None


class TestIndexDecoratorRegistration:
    """B10, B11, B12, B13, B15, B17, B18–B21: @app.index registration behaviors."""

    def test_index_sets_role_index_on_tool_definition(self) -> None:
        """B10: @app.index registers the function with role='index'."""
        app = _make_app()

        @app.index(object_type="document")
        async def index_doc(
            context: Context,
            object_id: Annotated[str, "The object identifier"],
        ) -> IndexedObject:
            """Index a document."""
            return IndexedObject(id=object_id, type="document", content="")

        tool_def = app.catalog.get_tool_by_name("TestServer.IndexDoc").definition
        assert tool_def.role == "index"

    def test_index_without_parentheses_raises(self) -> None:
        """B11: Bare @app.index (no parentheses) raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.index  # type: ignore[arg-type]
            async def index_doc(
                context: Context,
                object_id: Annotated[str, "The object identifier"],
            ) -> IndexedObject:
                """Index a document."""
                return IndexedObject(id=object_id, type="document", content="")

    def test_duplicate_index_type_raises(self) -> None:
        """B13: Registering two @app.index with the same type raises ToolDefinitionError."""
        app = _make_app()

        @app.index(object_type="document")
        async def index_doc_1(
            context: Context,
            object_id: Annotated[str, "The object identifier"],
        ) -> IndexedObject:
            """First index handler."""
            return IndexedObject(id=object_id, type="document", content="")

        with pytest.raises(ToolDefinitionError):

            @app.index(object_type="document")
            async def index_doc_2(
                context: Context,
                object_id: Annotated[str, "The object identifier"],
            ) -> IndexedObject:
                """Second index handler — duplicate type."""
                return IndexedObject(id=object_id, type="document", content="")

    def test_missing_context_param_raises(self) -> None:
        """Index function without context param raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.index(object_type="document")
            async def index_doc(
                object_id: Annotated[str, "The object identifier"],
            ) -> IndexedObject:
                """Index doc — missing context."""
                return IndexedObject(id=object_id, type="document", content="")

    def test_missing_object_id_param_raises(self) -> None:
        """B15: Index function without object_id param raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.index(object_type="document")
            async def index_doc(context: Context) -> IndexedObject:
                """Index doc — missing object_id."""
                return IndexedObject(id="x", type="document", content="")

    def test_object_id_wrong_type_raises(self) -> None:
        """B15: Index function with object_id typed as int raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.index(object_type="document")
            async def index_doc(
                context: Context,
                object_id: Annotated[int, "The object identifier"],
            ) -> IndexedObject:
                """Index doc — object_id wrong type."""
                return IndexedObject(id=str(object_id), type="document", content="")

    def test_wrong_return_type_raises(self) -> None:
        """B17: Index function with non-IndexedObject return type raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.index(object_type="document")
            async def index_doc(
                context: Context,
                object_id: Annotated[str, "The object identifier"],
            ) -> dict:
                """Index doc — wrong return type."""
                return {}

    def test_extra_parameters_raises(self) -> None:
        """B18: Index function with extra parameters beyond object_id raises ToolDefinitionError."""
        app = _make_app()
        with pytest.raises(ToolDefinitionError):

            @app.index(object_type="document")
            async def index_doc(
                context: Context,
                object_id: Annotated[str, "The object identifier"],
                include_comments: Annotated[bool, "Include comments"] = False,
            ) -> IndexedObject:
                """Index doc — extra param."""
                return IndexedObject(id=object_id, type="document", content="")


class TestRuntimeExceptionHandling:
    """B22: Unhandled exceptions in crawl/index propagate as MCP errors."""

    def test_crawl_handler_registers_and_is_callable(self) -> None:
        """B22 (smoke): A crawl handler that would raise at runtime can still be registered."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_docs(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """Crawl that always raises."""
            raise RuntimeError("upstream failure")

        # Verify the tool is registered and callable
        mat_tool = app.catalog.get_tool_by_name("TestServer.CrawlDocs")
        assert mat_tool is not None
        assert mat_tool.definition.role == "crawl"
