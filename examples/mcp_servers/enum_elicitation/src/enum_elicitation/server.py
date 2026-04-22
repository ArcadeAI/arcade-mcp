#!/usr/bin/env python3
"""enum_elicitation MCP server.

Demonstrates the full set of enum elicitation schemas introduced in
MCP 2025-11-25 (SEP-1330), plus default-value support (SEP-1034) and the
JSON Schema 2020-12 dialect enforcement (SEP-1613).

Each tool sends a different enum variant to ``context.ui.elicit``:

- ``pick_priority``     — UntitledSingleSelectEnumSchema  (plain ``enum``)
- ``pick_region``       — TitledSingleSelectEnumSchema    (``oneOf`` with ``const`` + ``title``)
- ``pick_tags``         — UntitledMultiSelectEnumSchema   (``type: array`` + ``items.enum``)
- ``pick_permissions``  — TitledMultiSelectEnumSchema     (``type: array`` + ``items.anyOf``)
- ``pick_legacy``       — LegacyTitledEnumSchema          (``enum`` + ``enumNames``)

Finally, ``configure_deployment`` combines several variants in one schema —
that's what a real integration will look like.
"""

import sys

from arcade_mcp_server import Context, MCPApp

app = MCPApp(
    name="enum_elicitation",
    version="1.0.0",
    log_level="DEBUG",
    instructions=(
        "Every tool in this server demonstrates a different MCP 2025-11-25 enum "
        "elicitation schema. Check the code and README to learn which variant is which."
    ),
)


# -----------------------------------------------------------------------------
# 1. UntitledSingleSelectEnumSchema — the simplest case
# -----------------------------------------------------------------------------


@app.tool
async def pick_priority(context: Context) -> str:
    """Ask the user to pick a priority from a plain ``enum`` list.

    Wire shape (requestedSchema.properties.priority):
        {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"}
    """
    result = await context.ui.elicit(
        "What priority should we assign to this ticket?",
        schema={
            "type": "object",
            "properties": {
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    # SEP-1034: default values pass through to the client.
                    "default": "medium",
                }
            },
            "required": ["priority"],
        },
    )
    if result.action != "accept":
        return f"User {result.action}ed the elicitation."
    return f"Priority: {result.content['priority']}"


# -----------------------------------------------------------------------------
# 2. TitledSingleSelectEnumSchema — oneOf with const + title
# -----------------------------------------------------------------------------


@app.tool
async def pick_region(context: Context) -> str:
    """Ask the user to pick a region — values are opaque ids, titles are for humans.

    Wire shape: ``oneOf`` list of ``{"const": <id>, "title": <label>}`` objects.
    """
    result = await context.ui.elicit(
        "Which region should we deploy to?",
        schema={
            "type": "object",
            "properties": {
                "region": {
                    "oneOf": [
                        {"const": "us-east-1", "title": "US East (N. Virginia)"},
                        {"const": "us-west-2", "title": "US West (Oregon)"},
                        {"const": "eu-west-1", "title": "EU West (Ireland)"},
                        {"const": "ap-southeast-2", "title": "Asia Pacific (Sydney)"},
                    ]
                }
            },
            "required": ["region"],
        },
    )
    if result.action != "accept":
        return f"User {result.action}ed the elicitation."
    return f"Region: {result.content['region']}"


# -----------------------------------------------------------------------------
# 3. UntitledMultiSelectEnumSchema — array of enum values
# -----------------------------------------------------------------------------


@app.tool
async def pick_tags(context: Context) -> str:
    """Ask the user to pick zero-or-more tags. Multi-select without titles.

    Wire shape: ``{"type": "array", "items": {"type": "string", "enum": [...]}}``.
    """
    result = await context.ui.elicit(
        "Which tags apply to this issue? (pick as many as you like)",
        schema={
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": ["bug", "feature", "docs", "regression", "good-first-issue"],
                    },
                    "default": [],
                }
            },
        },
    )
    if result.action != "accept":
        return f"User {result.action}ed the elicitation."
    tags = result.content.get("tags", [])
    return f"Selected tags: {', '.join(tags) if tags else '(none)'}"


# -----------------------------------------------------------------------------
# 4. TitledMultiSelectEnumSchema — array where items have titled anyOf
# -----------------------------------------------------------------------------


@app.tool
async def pick_permissions(context: Context) -> str:
    """Ask the user to grant one-or-more permission scopes with titled options.

    Wire shape: ``{"type": "array", "items": {"anyOf": [{"const": ..., "title": ...}, ...]}}``.
    """
    result = await context.ui.elicit(
        "Which permissions should we grant this token?",
        schema={
            "type": "object",
            "properties": {
                "permissions": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"const": "read", "title": "Read"},
                            {"const": "write", "title": "Write"},
                            {"const": "admin", "title": "Administer"},
                            {"const": "billing", "title": "Access Billing"},
                        ]
                    },
                    "default": ["read"],
                }
            },
            "required": ["permissions"],
        },
    )
    if result.action != "accept":
        return f"User {result.action}ed the elicitation."
    permissions = result.content.get("permissions", [])
    return f"Permissions: {', '.join(permissions) if permissions else '(none)'}"


# -----------------------------------------------------------------------------
# 5. LegacyTitledEnumSchema — enum + enumNames
# -----------------------------------------------------------------------------


@app.tool
async def pick_legacy(context: Context) -> str:
    """Legacy-form titled enum using parallel ``enum`` + ``enumNames`` arrays.

    The 2025-11-25 spec keeps this shape round-trippable for clients that still
    emit it, even though new integrations should prefer the ``oneOf`` form.
    """
    result = await context.ui.elicit(
        "Choose your shipping speed:",
        schema={
            "type": "object",
            "properties": {
                "speed": {
                    "enum": ["std", "exp", "ovn"],
                    "enumNames": ["Standard (5-7 days)", "Express (2-3 days)", "Overnight"],
                    "default": "std",
                }
            },
            "required": ["speed"],
        },
    )
    if result.action != "accept":
        return f"User {result.action}ed the elicitation."
    return f"Shipping speed: {result.content['speed']}"


# -----------------------------------------------------------------------------
# 6. Composite — the realistic case: multiple variants inside one schema
# -----------------------------------------------------------------------------


@app.tool
async def configure_deployment(context: Context) -> dict:
    """Ask the user to fill in a realistic deployment form that combines several
    enum variants inside one elicitation request.
    """
    result = await context.ui.elicit(
        "Configure the deployment:",
        schema={
            "type": "object",
            "properties": {
                "environment": {
                    # Titled single-select.
                    "oneOf": [
                        {"const": "dev", "title": "Development"},
                        {"const": "staging", "title": "Staging"},
                        {"const": "prod", "title": "Production"},
                    ]
                },
                "replicas": {
                    # Plain primitive with default (SEP-1034).
                    "type": "integer",
                    "default": 2,
                },
                "features": {
                    # Titled multi-select.
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"const": "canary", "title": "Canary rollout"},
                            {"const": "blue-green", "title": "Blue/green deploy"},
                            {"const": "autoscale", "title": "Autoscaling"},
                        ]
                    },
                    "default": ["canary"],
                },
                "notify": {
                    # Untitled single-select.
                    "type": "string",
                    "enum": ["me", "team", "nobody"],
                    "default": "team",
                },
            },
            "required": ["environment"],
        },
    )
    if result.action != "accept":
        return {"status": result.action}
    return {"status": "accepted", "config": result.content}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)
