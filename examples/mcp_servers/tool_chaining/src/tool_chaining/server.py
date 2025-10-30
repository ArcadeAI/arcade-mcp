#!/usr/bin/env python3
"""tool_calling_other_tools_programmatically MCP server"""

import hashlib
from typing import Annotated

from arcade_mcp_server import Context, MCPApp

app = MCPApp(name="ToolChainer", version="1.0.0", log_level="DEBUG")


@app.tool
def hash_text(text: Annotated[str, "The text to hash"]) -> str:
    """Hash the text"""
    return hashlib.sha256(text.encode()).hexdigest()


@app.tool(requires_secrets=["PASSWORD"])
async def get_password_as_hash_value(context: Context) -> str:
    """Get the hash value of the password"""
    elicitation_schema = {"type": "object", "properties": {"confirmation": {"type": "boolean"}}}
    result = await context.ui.elicit(
        "Are you sure you want to get the hash value of the password?",
        schema=elicitation_schema,
    )

    if result.action == "accept":
        return hash_text(context.get_secret("PASSWORD"))
    else:
        raise ValueError("User did not confirm the elicitation")


@app.tool(requires_secrets=["API_KEY"])
async def get_api_key_as_hash_value(context: Context) -> str:
    """Get the hash value of the API key"""
    return hash_text(context.get_secret("API_KEY"))


@app.tool
async def get_secret_as_hash_value(
    context: Context,
    secret_name: Annotated[str, "The name of the secret to get the hash value of"],
) -> str:
    """Get the hash value of a secret"""
    tool_name = ""
    if secret_name.upper() == "PASSWORD":
        tool_name = "ToolChainer_GetPasswordAsHashValue"
    elif secret_name.upper() == "API_KEY":
        tool_name = "ToolChainer_GetApiKeyAsHashValue"

    if not tool_name:
        return "Sorry, but I don't know how to get the hash value of that secret."

    hash_response = await context.tools.call_raw(tool_name, {})

    if hash_response.isError:
        return (
            "Sorry, but I couldn't get the hash value of the secret, because: "
            + hash_response.structuredContent["error"]
        )

    return hash_response.structuredContent["result"]


if __name__ == "__main__":
    app.run(transport="stdio")
