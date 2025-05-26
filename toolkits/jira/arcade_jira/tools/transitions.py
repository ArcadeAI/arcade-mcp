from typing import Annotated, cast

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.utils import remove_none_values


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_transitions_available_for_issue(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue"],
) -> Annotated[
    dict, "The transitions available (including screen fields) and the issue's current status"
]:
    """Get the transitions available for an existing Jira issue."""
    from arcade_jira.tools.issues import get_issue_by_id  # Avoid circular import

    client = JiraClient(context.get_auth_token_or_empty())
    issue_data = await get_issue_by_id(context, issue)
    if issue_data.get("error"):
        return cast(dict, issue_data)
    response = await client.get(
        f"/issue/{issue_data['issue']['id']}/transitions",
        params={
            "expand": "transitions.fields",
        },
    )
    return {
        "issue": {
            "id": issue_data["issue"]["id"],
            "key": issue_data["issue"]["key"],
            "current_status": issue_data["issue"]["status"],
        },
        "transitions_available": response["transitions"],
    }


@tool(requires_auth=Atlassian(scopes=["write:jira-work"]))
async def get_transition_by_name(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue"],
    transition: Annotated[str, "The name of the transition"],
) -> Annotated[dict, "The transition data, including screen fields available"]:
    """Get a transition available for an issue by the transition name.

    The response will contain screen fields available for the transition, if any.
    """
    transitions = await get_transitions_available_for_issue(context, issue)
    for available_transition in transitions["transitions_available"]:
        if available_transition["name"].casefold() == transition.casefold():
            return {"issue": issue, "transition": available_transition}
    return {
        "error": f"Transition '{transition}' not found for the issue '{issue}'",
        "transitions_available": transitions["transitions_available"],
    }


@tool(requires_auth=Atlassian(scopes=["write:jira-work"]))
async def perform_issue_transition(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue"],
    transition: Annotated[
        str,
        "The transition to perform. Provide the transition ID or its name (case insensitive).",
    ],
    fields: Annotated[
        dict | None,
        "List of issue screen fields to update, specifying the sub-field to update and its value "
        "for each field. Defaults to None (no fields updated). This argument provides a "
        "straightforward option when setting a sub-field. When multiple sub-fields or other "
        "operations are required, use the 'update' argument. Fields included in here cannot "
        "be included in the 'update' argument.",
    ] = None,
    update: Annotated[
        dict | None,
        "A Map containing the field field name and a list of operations to perform on the issue "
        "screen field. Defaults to None (no fields updated). Note that fields included in here "
        "cannot be included in the 'fields' argument.",
    ] = None,
) -> Annotated[dict, "The updated issue"]:
    """Transition an existing Jira issue."""
    client = JiraClient(context.get_auth_token_or_empty())

    if transition.isdigit():
        transition_id = transition
        transition_name = transition
    else:
        response = await get_transition_by_name(context, issue, transition)
        if response.get("error"):
            return cast(dict, response)
        transition_id = response["transition"]["id"]
        transition_name = response["transition"]["name"]

    # The /issue/issue_id/transitions endpoint returns a 204 No Content in case of success
    await client.post(
        f"/issue/{issue}/transitions",
        json_data=remove_none_values({
            "transition": {"id": transition_id},
            "fields": fields,
            "update": update,
        }),
    )

    return {
        "status": "success",
        "message": f"Issue '{issue}' successfully transitioned to '{transition_name}'.",
    }
