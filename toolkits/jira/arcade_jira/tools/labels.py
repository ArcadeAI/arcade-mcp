from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.utils import add_pagination_to_response, resolve_cloud_id


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def list_labels(
    context: ToolContext,
    limit: Annotated[
        int, "The maximum number of labels to return. Min of 1, Max of 200. Defaults to 200."
    ] = 200,
    offset: Annotated[
        int, "The number of labels to skip. Defaults to 0 (starts from the first label)"
    ] = 0,
    atlassian_cloud_id: Annotated[
        str | None,
        "The ID of the Atlassian Cloud to use (defaults to None). If not provided and the user has "
        "a single cloud authorized, the tool will use that. Otherwise, an error will be raised.",
    ] = None,
) -> Annotated[dict[str, Any], "The existing labels (tags) in the user's Jira instance"]:
    """Get the existing labels (tags) in the user's Jira instance."""
    limit = max(min(limit, 200), 1)
    atlassian_cloud_id = await resolve_cloud_id(context, atlassian_cloud_id)
    client = JiraClient(context=context, cloud_id=atlassian_cloud_id)
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
