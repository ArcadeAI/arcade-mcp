#!/usr/bin/env python3
"""
Tool Metadata Example MCP Server

This example demonstrates how to use tool metadata to describe your tools'
classification, behavior, and custom properties. Tool metadata helps with:

- Tool discovery and selection (classification)
- Policy decisions and MCP annotations (behavior)
- Custom logic like routing or feature flags (extras)
"""

import sys
from typing import Annotated

from arcade_mcp_server import MCPApp
from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Domain,
    SystemType,
    ToolMetadata,
    Verb,
)

app = MCPApp(name="ToolMetadataDemo", version="1.0.0", log_level="DEBUG")

# In-memory storage for demo purposes
_notes: dict[str, str] = {}


# =============================================================================
# Example 1: Pure computation tool (IN_PROCESS, read-only)
# =============================================================================
@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.TRANSFORM],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.EXECUTE],
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=False,  # No external systems
        ),
    ),
)
def reverse_text(text: Annotated[str, "The text to reverse"]) -> str:
    """Reverse the characters in a string. A pure computation with no side effects."""
    return text[::-1]


# =============================================================================
# Example 2: Read-only search tool
# =============================================================================
@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.SEARCH],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.READ],
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=False,
        ),
    ),
)
def search_notes(
    query: Annotated[str, "Search term to find in note titles and content"],
) -> list[dict[str, str]]:
    """Search through stored notes by title or content."""
    query_lower = query.lower()
    results = []
    for title, content in _notes.items():
        if query_lower in title.lower() or query_lower in content.lower():
            results.append({"title": title, "content": content})
    return results


# =============================================================================
# Example 3: Create tool (mutating, not destructive)
# =============================================================================
@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.DOCUMENTS],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.CREATE],
            read_only=False,
            destructive=False,  # Creating is not destructive
            idempotent=False,  # Creating twice may have different effects
            open_world=False,
        ),
    ),
)
def create_note(
    title: Annotated[str, "The title of the note"],
    content: Annotated[str, "The content of the note"],
) -> dict[str, str]:
    """Create a new note. Fails if a note with the same title already exists."""
    if title in _notes:
        return {"error": f"Note '{title}' already exists. Use update_note instead."}
    _notes[title] = content
    return {"status": "created", "title": title}


# =============================================================================
# Example 4: Update tool (mutating, idempotent)
# =============================================================================
@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.DOCUMENTS],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.UPDATE],
            read_only=False,
            destructive=False,
            idempotent=True,  # Updating with same content is idempotent
            open_world=False,
        ),
    ),
)
def update_note(
    title: Annotated[str, "The title of the note to update"],
    content: Annotated[str, "The new content for the note"],
) -> dict[str, str]:
    """Update an existing note's content."""
    if title not in _notes:
        return {"error": f"Note '{title}' not found. Use create_note first."}
    _notes[title] = content
    return {"status": "updated", "title": title}


# =============================================================================
# Example 5: Delete tool (destructive!)
# =============================================================================
@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.DOCUMENTS],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.DELETE],
            read_only=False,
            destructive=True,  # Deletion is destructive - data is lost
            idempotent=True,  # Deleting twice has same effect as once
            open_world=False,
        ),
    ),
)
def delete_note(
    title: Annotated[str, "The title of the note to delete"],
) -> dict[str, str]:
    """Permanently delete a note. This action cannot be undone."""
    if title not in _notes:
        return {"error": f"Note '{title}' not found."}
    del _notes[title]
    return {"status": "deleted", "title": title}


# =============================================================================
# Example 6: Tool with extras for custom logic
# =============================================================================
@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.ANALYTICS],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.READ],
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=False,
        ),
        # Extras: arbitrary key/values for custom logic
        # These don't affect tool selection, but can be used for:
        # - Routing decisions (e.g., which IDP to use)
        # - Feature flags
        # - Rate limiting
        # - Governance/compliance metadata
        extras={
            "billing_tier": "free",  # Feature flag for billing
            "max_requests_per_minute": 100,  # Rate limiting hint
            "data_classification": "internal",  # Compliance metadata
            "cache_ttl_seconds": 60,  # Caching hint
        },
    ),
)
def get_notes_stats() -> dict[str, int]:
    """Get statistics about stored notes. Demonstrates the 'extras' field."""
    total_notes = len(_notes)
    total_chars = sum(len(content) for content in _notes.values())
    return {
        "total_notes": total_notes,
        "total_characters": total_chars,
        "average_length": total_chars // total_notes if total_notes > 0 else 0,
    }


# =============================================================================
# Example 7: Multi-verb tool (upsert = CREATE + UPDATE)
# =============================================================================
@app.tool(
    metadata=ToolMetadata(
        classification=Classification(
            domains=[Domain.DOCUMENTS],
            system_types=[SystemType.IN_PROCESS],
        ),
        behavior=Behavior(
            verbs=[Verb.CREATE, Verb.UPDATE],  # Multiple verbs for compound actions
            read_only=False,
            destructive=False,
            idempotent=True,  # Upsert is idempotent
            open_world=False,
        ),
    ),
)
def upsert_note(
    title: Annotated[str, "The title of the note"],
    content: Annotated[str, "The content of the note"],
) -> dict[str, str]:
    """Create or update a note. If the note exists, it will be updated."""
    action = "updated" if title in _notes else "created"
    _notes[title] = content
    return {"status": action, "title": title}


# Run with specific transport
if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    app.run(transport=transport, host="127.0.0.1", port=8000)
