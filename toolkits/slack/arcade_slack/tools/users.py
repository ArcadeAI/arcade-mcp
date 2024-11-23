from typing import Annotated

from slack_sdk import WebClient

from arcade.core.errors import ToolExecutionError
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Slack


@tool(
    requires_auth=Slack(
        scopes=["users:read", "users:read.email"],
    )
)
def get_user_info_by_id(
    context: ToolContext,
    user_id: Annotated[str, "The ID of the user to get"],
) -> Annotated[dict, "The user's information"]:
    """Get the information of a user in Slack."""

    slackClient = WebClient(token=context.authorization.token)
    response = slackClient.users_info(user=user_id)
    if not response.get("ok"):
        raise ToolExecutionError(
            "Failed to get user info.",
            developer_message=f"Failed to get user info: {response.get('error')}",
        )
    return response.get("user", {})


@tool(
    requires_auth=Slack(
        scopes=["users:read", "users:read.email"],
    )
)
def list_users(
    context: ToolContext,
    limit: Annotated[int, "The maximum number of users to return. Defaults to -1 (no limit)"] = -1,
) -> Annotated[dict, "The users' info"]:
    """List all users in Slack team."""

    slackClient = WebClient(token=context.authorization.token)
    users = []
    next_page_token = None

    while limit == -1 or len(users) < limit:
        iteration_limit = (
            200 if limit == -1 else min(limit - len(users), 200)
        )  # Slack recommends max 200 results at a time
        response = slackClient.users_list(cursor=next_page_token, limit=iteration_limit)
        if not response.get("ok"):
            raise ToolExecutionError(
                "Failed to get user info.",
                developer_message=f"Failed to get user info: {response.get('error')}",
            )

        users.extend(response.get("members", []))
        next_page_token = response.get("response_metadata", {}).get("next_cursor")

        if not next_page_token:
            break

    return {"users": users}  # TODO: Returns too much info. Filter out a lot of it.
