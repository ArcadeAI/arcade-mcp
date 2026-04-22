# enum_elicitation

Demonstrates **every enum elicitation schema variant** introduced in
MCP 2025-11-25 (SEP-1330), together with default-value support (SEP-1034) and
the JSON Schema 2020-12 dialect enforcement (SEP-1613).

## Schema variants, one tool each

| Tool | Variant | Wire shape |
|---|---|---|
| `pick_priority` | `UntitledSingleSelectEnumSchema` | `{"type": "string", "enum": [...], "default": "..."}` |
| `pick_region` | `TitledSingleSelectEnumSchema` | `{"oneOf": [{"const": id, "title": label}, ...]}` |
| `pick_tags` | `UntitledMultiSelectEnumSchema` | `{"type": "array", "items": {"enum": [...]}}` |
| `pick_permissions` | `TitledMultiSelectEnumSchema` | `{"type": "array", "items": {"anyOf": [{"const": id, "title": label}, ...]}}` |
| `pick_legacy` | `LegacyTitledEnumSchema` | `{"enum": [...], "enumNames": [...]}` |
| `configure_deployment` | mixed | all of the above inside one elicitation |

## Running

```bash
uv sync
uv run python src/enum_elicitation/server.py        # stdio
uv run python src/enum_elicitation/server.py http   # HTTP+SSE
```

The server only emits elicitations in response to tool calls. To trigger them,
call each tool from an MCP client that supports elicitation (Claude Desktop,
Cursor, MCP Inspector).

## What you'll see on the wire

Calling `pick_region` produces an `elicitation/create` request with:

```jsonc
{
  "method": "elicitation/create",
  "params": {
    "message": "Which region should we deploy to?",
    "requestedSchema": {
      "type": "object",
      "properties": {
        "region": {
          "oneOf": [
            {"const": "us-east-1", "title": "US East (N. Virginia)"},
            {"const": "us-west-2", "title": "US West (Oregon)"},
            ...
          ]
        }
      },
      "required": ["region"]
    }
  }
}
```

The client MAY render that as a dropdown / radio group / autocomplete — SEP-1330
intentionally leaves the UI choice up to the client.

## Default values (SEP-1034)

Any of the primitive property schemas can include a `"default"` key. The
server passes it through unchanged; an MCP 2025-11-25 client pre-fills the form
with that default. Shown in `pick_priority` (`"default": "medium"`),
`pick_legacy` (`"default": "std"`), and `configure_deployment` (defaults on
every field).

## JSON Schema 2020-12 is the default dialect (SEP-1613)

`context.ui.elicit` now rejects schemas whose `$schema` isn't a 2020-12 URI.
In practice you rarely set `$schema` explicitly — omitting it uses the MCP
default, which is 2020-12 — but if you copy an older schema verbatim:

```python
await context.ui.elicit(
    "…",
    schema={
        "$schema": "https://json-schema.org/draft/2019-09/schema",  # ⚠️
        "type": "object",
        "properties": {...},
    },
)
```

…you get a clean error at call time rather than a silent wire-format mismatch:

```
ValueError: Unsupported $schema dialect. Elicitation schemas must use the
JSON Schema 2020-12 dialect.
```

## Common validation errors

The `UI._validate_elicitation_schema` path also rejects:

- **Non-primitive property types** that aren't `"array"` with a multi-select
  items schema: `ValueError: Property 'x' has unsupported type 'object'.`
- **String formats** outside the allowed set (`email`, `uri`, `date`, `date-time`).
- **Non-object top-level schemas** (`ValueError: Schema must have type 'object'`).

## Action dispatch

Every tool in this example handles the three `ElicitResult.action` values:

```python
if result.action == "accept":
    # result.content is a dict that matches the schema
    ...
elif result.action == "decline":
    # user refused
    ...
elif result.action == "cancel":
    # user aborted
    ...
```

## Related SEPs

- **SEP-1330** — Enum schema variants for elicitation.
- **SEP-1034** — Default values on elicitation primitive schemas.
- **SEP-1613** — JSON Schema 2020-12 as the default dialect.
