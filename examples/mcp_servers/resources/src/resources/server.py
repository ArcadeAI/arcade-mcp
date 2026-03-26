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
"""

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from arcade_mcp_server import Annotations, MCPApp
from resources.data import KB_ARTICLES, KB_CATEGORIES

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Get transport from command line argument, default to "stdio"
    # - "stdio" (default): Standard I/O for Claude Desktop, CLI tools, etc.
    # - "http": HTTPS streaming for Cursor, VS Code, etc.
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
