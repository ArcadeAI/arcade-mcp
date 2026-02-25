from typing import Annotated, Any

from arcade_mcp_server import Context, tool
from arcade_mcp_server.auth import OAuth2
from arcade_mcp_server.metadata import (
    Behavior,
    Classification,
    Operation,
    ServiceDomain,
    ToolMetadata,
)

from arcade_zendesk.who_am_i_util import build_who_am_i_response


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
    metadata=ToolMetadata(
        classification=Classification(
            service_domains=[ServiceDomain.CUSTOMER_SUPPORT],
        ),
        behavior=Behavior(
            operations=[Operation.READ],
            read_only=True,
            destructive=False,
            idempotent=True,
            open_world=True,
        ),
    ),
)
async def who_am_i(
    context: Context,
) -> Annotated[
    dict[str, Any],
    "Get comprehensive user profile and Zendesk account information.",
]:
    """
    Get comprehensive user profile and Zendesk account information.

    This tool provides detailed information about the authenticated user including
    their name, email, role, organization details, and Zendesk account context.
    """
    user_info = await build_who_am_i_response(context)
    return dict(user_info)
