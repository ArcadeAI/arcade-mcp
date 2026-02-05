# Tool Metadata Example

This example demonstrates how to use **tool metadata** to describe your tools' classification, behavior, and custom properties.

## What is Tool Metadata?

Tool metadata provides structured information about what a tool does:

| Field | Purpose | Used For |
|-------|---------|----------|
| **Classification** | What the tool is for, what it connects to | Tool discovery & selection boosting |
| **Behavior** | What effects the tool has | Policy decisions, MCP annotations |
| **Extras** | Arbitrary key/values | Custom logic (routing, rate limits, etc.) |

## Classification

Describes *what* the tool does and *what systems* it interfaces with.

```python
classification=Classification(
    domains=[Domain.DOCUMENTS],      # What capability area?
    system_types=[SystemType.IN_PROCESS],  # What system type?
)
```

**Domains** (what the tool does): `MESSAGING`, `DOCUMENTS`, `SEARCH`, `TRANSFORM`, `ANALYTICS`, etc.

**System Types** (what it connects to): `SAAS_API`, `DATABASE`, `IN_PROCESS`, `WEB`, etc.

## Behavior

Describes the tool's *effects* and maps to MCP annotations.

```python
behavior=Behavior(
    verbs=[Verb.CREATE],     # What action? READ, CREATE, UPDATE, DELETE, EXECUTE
    read_only=False,         # Does it only read data?
    destructive=False,       # Can it cause irreversible data loss?
    idempotent=True,         # Are repeated calls safe?
    open_world=False,        # Does it interact with external systems?
)
```

These values become MCP `annotations` that clients like Claude can use to make informed decisions.

## Extras

Arbitrary key/values for custom logic that *don't* affect tool selection.

```python
extras={
    "billing_tier": "free",
    "max_requests_per_minute": 100,
    "data_classification": "internal",
}
```

Use extras for: IDP routing, feature flags, rate limiting hints, compliance metadata.

## Running the Example

```bash
cd examples/mcp_servers/tool_metadata

# Install dependencies
uv sync

# Run with stdio transport
uv run src/tool_metadata/server.py stdio

# Or run with HTTP transport
uv run src/tool_metadata/server.py http
```

## Tools in This Example

| Tool | Verbs | Behavior | Notes |
|------|-------|----------|-------|
| `reverse_text` | EXECUTE | read_only, idempotent | Pure computation |
| `search_notes` | READ | read_only, idempotent | Query data |
| `create_note` | CREATE | not idempotent | Creates new data |
| `update_note` | UPDATE | idempotent | Modifies existing data |
| `delete_note` | DELETE | destructive, idempotent | Removes data permanently |
| `get_notes_stats` | READ | read_only | Has `extras` for custom metadata |
| `upsert_note` | CREATE, UPDATE | idempotent | Multi-verb compound action |
