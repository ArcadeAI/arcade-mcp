"""Tests for crawl & index capability discovery via tools/list.

Covers spec behaviors B23–B25:
  .project/specs/crawl-index-capabilities.md
"""

from typing import Annotated

from arcade_core.catalog import ToolCatalog
from arcade_core.schema import CrawlResult, IndexedObject
from arcade_mcp_server.context import Context
from arcade_mcp_server.convert import create_mcp_tool
from arcade_mcp_server.mcp_app import MCPApp


def _make_app() -> MCPApp:
    return MCPApp(name="DriveServer", version="1.0.0")


class TestCrawlIndexDiscovery:
    """B23–B25: _meta.arcade fields in tools/list output."""

    def test_crawl_handler_has_role_and_object_type_in_meta(self) -> None:
        """B23: Crawl handler appears in tools/list with role='crawl' and object_type set."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_documents(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """Crawl Google Drive documents."""
            return CrawlResult()

        mat_tool = app.catalog.get_tool_by_name("DriveServer.CrawlDocuments")
        mcp_tool = create_mcp_tool(mat_tool)

        arcade_meta = mcp_tool.meta["arcade"]
        assert arcade_meta["role"] == "crawl"
        assert arcade_meta["object_type"] == "document"

    def test_index_handler_has_role_and_object_type_in_meta(self) -> None:
        """B23: Index handler appears in tools/list with role='index' and object_type set."""
        app = _make_app()

        @app.index(object_type="document")
        async def index_document(
            context: Context,
            object_id: Annotated[str, "The object identifier"],
        ) -> IndexedObject:
            """Index a Google Drive document."""
            return IndexedObject(id=object_id, type="document", content="")

        mat_tool = app.catalog.get_tool_by_name("DriveServer.IndexDocument")
        mcp_tool = create_mcp_tool(mat_tool)

        arcade_meta = mcp_tool.meta["arcade"]
        assert arcade_meta["role"] == "index"
        assert arcade_meta["object_type"] == "document"

    def test_regular_tool_has_role_tool_in_meta(self) -> None:
        """B24: Regular @app.tool has role='tool' in _meta.arcade."""
        from arcade_mcp_server import tool

        @tool
        def list_files(path: Annotated[str, "Directory path"]) -> str:
            """List files in a directory."""
            return ""

        catalog = ToolCatalog()
        catalog.add_tool(list_files, "DriveServer")
        mat_tool = next(iter(catalog))
        mcp_tool = create_mcp_tool(mat_tool)

        arcade_meta = mcp_tool.meta["arcade"]
        assert arcade_meta["role"] == "tool"

    def test_multiple_crawl_types_each_have_correct_object_type(self) -> None:
        """EC1/B23: Multiple crawl handlers each expose their own object_type."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_documents(
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

        doc_tool = create_mcp_tool(app.catalog.get_tool_by_name("DriveServer.CrawlDocuments"))
        sheet_tool = create_mcp_tool(app.catalog.get_tool_by_name("DriveServer.CrawlSheets"))

        assert doc_tool.meta["arcade"]["object_type"] == "document"
        assert sheet_tool.meta["arcade"]["object_type"] == "sheet"

    def test_platform_can_find_crawl_handler_by_type(self) -> None:
        """B25: Platform discovery — filter tools/list by role and object_type (case-insensitive)."""
        app = _make_app()

        @app.crawl(object_type="document")
        async def crawl_documents(
            context: Context,
            cursor: Annotated[str | None, "Pagination cursor"] = None,
        ) -> CrawlResult:
            """Crawl documents."""
            return CrawlResult()

        mcp_tools = [create_mcp_tool(t) for t in app.catalog]

        # Simulate platform lookup: find crawl handler for type "Document" (case-insensitive)
        matches = [
            t
            for t in mcp_tools
            if t.meta
            and t.meta.get("arcade", {}).get("role") == "crawl"
            and t.meta.get("arcade", {}).get("object_type", "").lower() == "document"
        ]
        assert len(matches) == 1
        assert matches[0].meta["arcade"]["object_type"] == "document"
