from typing import Annotated

import httpx
from arcade_mcp_server import tool
from arcade_tdk import ToolContext
from arcade_tdk.auth import Google

from app_tools.ui import editor


@tool(ui=editor)
def preview_greeting(name: Annotated[str, "The name to greet"]) -> Annotated[str, "A greeting"]:
    """Show a greeting editor. The user can edit the name and call other tools in the App."""
    return f"Hello, {name}!"


@tool
def uppercase_greeting(
    name: Annotated[str, "The name to greet"],
) -> Annotated[str, "An uppercase greeting"]:
    """Return an uppercase greeting for the name. Does not change any saved data."""
    return f"Hello, {name}!".upper()


@tool(requires_auth=Google(scopes=["https://www.googleapis.com/auth/userinfo.profile"]))
async def google_profile(
    context: ToolContext,
    name: Annotated[str, "The name to greet"],
) -> Annotated[str, "A greeting with the authorized Google account's display name"]:
    """Read the user's Google profile and add the account name to the greeting."""
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {context.get_auth_token_or_empty()}"},
        )
        response.raise_for_status()
    profile_name = response.json().get("name", "Google user")
    return f"Hello, {name}! Google account: {profile_name}."
