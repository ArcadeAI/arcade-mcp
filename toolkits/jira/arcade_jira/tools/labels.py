from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.utils import add_pagination_to_response


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def list_labels(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of labels to return. Min of 1, Max of 200. Defaults to 200."
    ] = 200,
    offset: Annotated[
        int, "The number of labels to skip. Defaults to 0 (starts from the first label)"
    ] = 0,
) -> Annotated[dict[str, Any], "The existing labels (tags) in the user's Jira instance"]:
    """Get the existing labels (tags) in the user's Jira instance."""
    limit = max(min(limit, 200), 1)
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        "/label",
        params={
            "maxResults": limit,
            "startAt": offset,
        },
    )
    response = {
        "labels": api_response["values"],
        "total": api_response["total"],
    }
    return add_pagination_to_response(response, api_response["values"], limit, offset)
