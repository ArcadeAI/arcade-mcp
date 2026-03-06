# Tool Metadata Example

This example demonstrates how to use **tool metadata** to describe your tools' classification, behavior, and custom properties.

## What is Tool Metadata?

Tool metadata provides structured information about what a tool does:

| Field | Purpose | Used For |
|-------|---------|----------|
| **Classification** | What type of service the tool interfaces with | Tool discovery & selection boosting |
| **Behavior** | What effects the tool has | Policy decisions, MCP annotations |
| **Extras** | Arbitrary key/values | Custom logic (routing, rate limits, etc.) |

## Classification

Describes *what type of service* the tool interfaces with.

```python
classification=Classification(
    service_domains=[ServiceDomain.EMAIL],  # What type of service?
)
```

**Service Domains** (what type of service): `EMAIL`, `CRM`, `MESSAGING`, `DOCUMENTS`, `CLOUD_STORAGE`, `SOURCE_CODE`, `PAYMENTS`, `SOCIAL_MEDIA`, etc.

For tools with no external service (`open_world=False`), classification is `None`.

## Behavior

Describes the tool's *effects* and maps to MCP annotations.

```python
behavior=Behavior(
    operations=[Operation.CREATE],  # What effect? READ, CREATE, UPDATE, DELETE, OPAQUE
    read_only=False,                # Does it only read data?
    destructive=False,              # Can it cause irreversible data loss?
    idempotent=True,                # Are repeated calls safe?
    open_world=False,               # Does it interact with external systems?
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

| Tool | Operations | Behavior | Notes |
|------|------------|----------|-------|
| `reverse_text` | READ | read_only, idempotent | Pure computation |
| `search_notes` | READ | read_only, idempotent | Query data |
| `create_note` | CREATE | not idempotent | Creates new data |
| `update_note` | UPDATE | idempotent | Modifies existing data |
| `delete_note` | DELETE | destructive, idempotent | Removes data permanently |
| `get_notes_stats` | READ | read_only | Has `extras` for custom metadata |
| `upsert_note` | CREATE, UPDATE | idempotent | Multi-operation compound action |
