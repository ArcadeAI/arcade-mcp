#!/usr/bin/env python3
"""
Resources Example MCP Server

Comprehensive showcase of MCP resource features in arcade-mcp-server:

 1. @app.resource(uri) decorator        — register a resource with a handler
 2. app.add_resource(uri, handler=...)   — imperative registration
 3. app.add_text_resource(uri, text=...) — static text convenience
 4. app.add_file_resource(uri, path=...) — file-backed resource
 5. URI templates with {param}           — parameterized resources
 6. Wildcard templates {param*}          — greedy path matching
 7. Annotations(priority=...)            — resource annotations
 8. meta={...}                           — custom metadata
 9. Async handlers + return types        — bytes, dict, str
10. @app.tool(ui_resource_uri=...)       — MCP Apps (tool-to-UI linking)
11. Nested TypedDict tool outputs        — recursive structured output schemas
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from arcade_mcp_server import Annotations, MCPApp
from resources.data import KB_ARTICLES, KB_CATEGORIES, TEAMS
from resources.types import ArticleDetail, Author, SearchMatch, SearchResult

app = MCPApp(name="resources", version="1.0.0", log_level="DEBUG")

_HERE = Path(__file__).parent


# ===========================================================================
# 1. @app.resource decorator
# ===========================================================================
# The simplest way to register a resource with a handler function.
# The handler receives the URI as its first argument and returns content.


@app.resource(
    "kb://articles/index",
    name="Article Index",
    description="List of all knowledge base articles",
    mime_type="application/json",
)
def article_index(uri: str) -> str:
    """Return a JSON index of all articles."""
    index = [
        {"slug": slug, "title": a["title"], "category": a["category"]}
        for slug, a in KB_ARTICLES.items()
    ]
    return json.dumps(index, indent=2)


# ===========================================================================
# 2. app.add_resource — imperative registration
# ===========================================================================
# Use this when you want to register a resource without a decorator,
# for example when the handler is defined elsewhere or generated dynamically.


def _serve_category_list(uri: str) -> str:
    """Return the list of categories as JSON."""
    return json.dumps(list(KB_CATEGORIES.keys()))


app.add_resource(
    "kb://categories",
    name="Categories",
    description="List of all article categories",
    mime_type="application/json",
    handler=_serve_category_list,
)


# ===========================================================================
# 3. app.add_text_resource — static text convenience
# ===========================================================================
# One-liner for resources whose content is known at registration time.
# No handler function needed — the text is served directly.

app.add_text_resource(
    "kb://readme",
    text="Welcome to the Company Knowledge Base.\n\nBrowse articles by category or search by slug.",
    name="README",
    description="Knowledge base welcome text",
)


# ===========================================================================
# 4. app.add_file_resource — file-backed resource
# ===========================================================================
# Serves a file from disk. Text files are returned as TextResourceContents;
# binary files (detected via UnicodeDecodeError) as BlobResourceContents.

app.add_file_resource(
    "kb://config/pyproject",
    path=_HERE.resolve().parents[1] / "pyproject.toml",
    name="Project Config",
    description="The pyproject.toml for this example server",
    mime_type="text/plain",
)


# ===========================================================================
# 5. URI templates with {param}
# ===========================================================================
# When a URI contains {braces}, it is automatically registered as a
# ResourceTemplate. The handler receives extracted parameters as kwargs.


@app.resource(
    "kb://articles/{slug}",
    name="Article by Slug",
    description="Retrieve a specific article by its slug",
    mime_type="application/json",
)
def article_by_slug(uri: str, slug: str) -> str:
    """Return a single article as JSON. 'slug' is extracted from the URI."""
    article = KB_ARTICLES.get(slug)
    if article is None:
        return json.dumps({"error": f"Article '{slug}' not found"})
    return json.dumps(article, indent=2)


# Multi-parameter template — both {category} and {slug} are extracted.
@app.resource(
    "kb://categories/{category}/articles/{slug}",
    name="Article by Category and Slug",
    description="Retrieve an article scoped to a category",
    mime_type="application/json",
)
def article_in_category(uri: str, category: str, slug: str) -> str:
    """Return an article only if it belongs to the given category."""
    if category not in KB_CATEGORIES:
        return json.dumps({"error": f"Category '{category}' not found"})
    if slug not in KB_CATEGORIES[category]:
        return json.dumps({"error": f"Article '{slug}' not in category '{category}'"})
    return json.dumps(KB_ARTICLES[slug], indent=2)


# ===========================================================================
# 6. Wildcard templates {param*}
# ===========================================================================
# The {param*} syntax matches greedily across '/' separators, useful for
# nested paths like "guides/setup/linux".


@app.resource(
    "kb://docs/{path*}",
    name="Docs Tree",
    description="Retrieve documentation by nested path (e.g. 'guides/setup/linux')",
    mime_type="text/plain",
)
def docs_by_path(uri: str, path: str) -> str:
    """Wildcard match — 'path' captures everything including slashes."""
    return f"You requested documentation at path: {path}\n(In a real server, this would read from a docs tree.)"


# ===========================================================================
# 7. Annotations
# ===========================================================================
# Resource annotations let clients sort, filter, or prioritize resources.
# The Annotations model supports 'audience' and 'priority' fields.


@app.resource(
    "kb://announcements/pinned",
    name="Pinned Announcement",
    description="The current pinned company announcement",
    mime_type="text/plain",
    annotations=Annotations(
        audience=["user"],
        priority=1.0,
    ),
)
def pinned_announcement(uri: str) -> str:
    """A high-priority resource. Clients can use annotations to sort/filter."""
    return "All-hands meeting this Friday at 3 PM."


# ===========================================================================
# 8. Custom metadata (meta)
# ===========================================================================
# Arbitrary metadata attached to a resource, visible to clients in
# resources/list responses under the _meta field.


@app.resource(
    "kb://articles/api-guidelines/metadata",
    name="API Guidelines Metadata",
    description="Article with custom metadata tags",
    mime_type="application/json",
    meta={"tags": ["api", "engineering", "standards"], "version": 2, "reviewed": True},
)
def article_metadata(uri: str) -> str:
    """Resource with custom _meta fields. Clients see these in resources/list."""
    return json.dumps(KB_ARTICLES["api-guidelines"], indent=2)


# ===========================================================================
# 9. Async handlers + return types
# ===========================================================================
# Handlers can be async. Return types are automatically coerced:
#   - str  → TextResourceContents
#   - bytes → BlobResourceContents (base64-encoded)
#   - dict with "text" key → TextResourceContents
#   - dict with "blob" key → BlobResourceContents

# Static PNG file — demonstrates binary file-backed resources.
app.add_file_resource(
    "kb://branding/logo",
    path=_HERE / "logo.png",
    name="Company Logo",
    description="A small 32x32 pixel-art KB logo (binary file resource)",
    mime_type="image/png",
)


@app.resource(
    "kb://status",
    name="Server Status",
    description="Server health status (async handler returning dict)",
    mime_type="application/json",
)
async def server_status(uri: str) -> dict:
    """Async handler returning dict with 'text' key → TextResourceContents."""
    await asyncio.sleep(0)  # simulate async I/O
    status = {
        "healthy": True,
        "article_count": len(KB_ARTICLES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return {"text": json.dumps(status, indent=2)}


# ===========================================================================
# 10. MCP Apps — tool-to-UI resource linking with nested TypedDict outputs
# ===========================================================================
# Tools can declare a ui_resource_uri to link them to an interactive HTML
# resource. MCP Apps hosts render the HTML in a sandboxed iframe and the UI
# can call tools back on the server via postMessage JSON-RPC.
#
# These tools also showcase nested TypedDict return types, which
# arcade-mcp-server recursively expands into full JSON Schema output schemas.
#
# See: https://modelcontextprotocol.io/extensions/apps/build

APP_RESOURCE_URI = "ui://resources/mcp-app.html"


@app.tool(ui_resource_uri=APP_RESOURCE_URI)
def get_article(
    slug: Annotated[str, "The article slug (e.g. 'getting-started')"],
) -> Annotated[ArticleDetail, "Full article with nested author information"]:
    """Retrieve a knowledge-base article by slug, including author details.

    Returns an ArticleDetail (nested TypedDict) with a nested Author object,
    demonstrating recursive structured output schemas.
    """
    raw = KB_ARTICLES.get(slug)
    if raw is None:
        raise ValueError(f"Article '{slug}' not found")
    return ArticleDetail(
        slug=slug,
        title=raw["title"],
        category=raw["category"],
        body=raw["body"],
        author=TEAMS.get(raw["author"], Author(name=raw["author"], team="Unknown")),
    )


@app.tool(ui_resource_uri=APP_RESOURCE_URI)
def search_articles(
    query: Annotated[str, "Case-insensitive search query"],
) -> Annotated[SearchResult, "Search results with nested match details"]:
    """Search knowledge-base articles by title, category, or body text.

    Returns a SearchResult (nested TypedDict) containing a list of SearchMatch
    objects, demonstrating recursive structured output schemas with lists.
    """
    q = query.lower()
    matches: list[SearchMatch] = []
    for slug, article in KB_ARTICLES.items():
        for field in ("title", "category", "body"):
            if q in article[field].lower():
                matches.append(
                    SearchMatch(
                        slug=slug,
                        title=article["title"],
                        category=article["category"],
                        matched_field=field,
                    )
                )
                break  # one match per article
    return SearchResult(
        query=query,
        total_matches=len(matches),
        matches=matches,
    )


@app.resource(APP_RESOURCE_URI, name="MCP App UI", mime_type="text/html;profile=mcp-app")
def serve_app_ui(uri: str) -> str:
    """Serve the MCP App HTML from the co-located app.html file."""
    return (_HERE / "app.html").read_text()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
