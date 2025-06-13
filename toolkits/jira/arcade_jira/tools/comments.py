from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian
from arcade_tdk.errors import ToolExecutionError

from arcade_jira.client import JiraClient
from arcade_jira.constants import IssueCommentOrderBy
from arcade_jira.exceptions import MultipleItemsFoundError, NotFoundError
from arcade_jira.utils import (
    add_pagination_to_response,
    build_adf_doc,
    clean_comment_dict,
    find_multiple_unique_users,
    remove_none_values,
)


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_comment_by_id(
    context: ToolContext,
    issue_id: Annotated[str, "The ID or key of the issue to retrieve the comment from."],
    comment_id: Annotated[str, "The ID of the comment to retrieve"],
    include_adf_content: Annotated[
        bool,
        "Whether to include the ADF (Atlassian Document Format) content of the comment in the "
        "response. Defaults to False (return only the HTML rendered content).",
    ] = False,
) -> Annotated[dict[str, Any], "Information about the comment"]:
    """Get a comment by its ID."""
    client = JiraClient(context.get_auth_token_or_empty())
    response = await client.get(
        f"issue/{issue_id}/comment/{comment_id}",
        params={"expand": "renderedBody"},
    )

    if not response:
        return {
            "comment": None,
            "message": f"No comment found with ID '{comment_id}' in the issue '{issue_id}'.",
            "query": {"issue_id": issue_id, "comment_id": comment_id},
        }

    return {"comment": clean_comment_dict(response, include_adf_content)}


@tool(requires_auth=Atlassian(scopes=["read:jira-work"]))
async def get_issue_comments(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to retrieve"],
    limit: Annotated[
        int,
        "The maximum number of comments to retrieve. Min 1, max 100, default 100.",
    ] = 100,
    offset: Annotated[
        int,
        "The number of comments to skip. Defaults to 0 (start from the first comment).",
    ] = 0,
    order_by: Annotated[
        IssueCommentOrderBy | None,
        "The order in which to return the comments. "
        f"Defaults to '{IssueCommentOrderBy.CREATED_DATE_DESCENDING.value}' (most recent first).",
    ] = IssueCommentOrderBy.CREATED_DATE_DESCENDING,
    include_adf_content: Annotated[
        bool,
        "Whether to include the ADF (Atlassian Document Format) content of the comment in the "
        "response. Defaults to False (return only the HTML rendered content).",
    ] = False,
) -> Annotated[dict[str, Any], "Information about the issue comments"]:
    """Get the comments of a Jira issue by its ID."""
    limit = max(min(limit, 100), 1)
    client = JiraClient(context.get_auth_token_or_empty())
    api_response = await client.get(
        f"issue/{issue}/comment",
        params=remove_none_values({
            "expand": "renderedBody",
            "maxResults": limit,
            "startAt": offset,
            "orderBy": order_by.to_api_value() if order_by else None,
        }),
    )
    comments = [
        clean_comment_dict(comment, include_adf_content)
        for comment in api_response["comments"][:limit]
    ]
    response = {
        "issue": issue,
        "comments": comments,
        "isLast": api_response.get("isLast"),
    }
    return add_pagination_to_response(response, comments, limit, offset)


@tool(
    requires_auth=Atlassian(
        scopes=[
            "write:jira-work",  # Needed to add the comment
            "read:jira-work",  # Needed to get the issue data
            "read:jira-user",  # Needed to resolve user ID from name or email (mention_users)
        ],
    ),
)
async def add_comment_to_issue(
    context: ToolContext,
    issue: Annotated[str, "The ID or key of the issue to comment on."],
    body: Annotated[str, "The body of the comment to add to the issue."],
    reply_to_comment: Annotated[
        str | None,
        "Quote a previous comment as a reply to it. Provide the comment's ID. "
        "Must be a comment from the same issue. Defaults to None (no quoted comment).",
    ] = None,
    mention_users: Annotated[
        list[str] | None,
        "The users to mention in the comment. Provide the user display name, email address, or ID. "
        "Ex: 'John Doe' or 'john.doe@example.com'. Defaults to None (no user mentions).",
    ] = None,
) -> Annotated[dict[str, Any], "Information about the comment created"]:
    """Add a comment to a Jira issue."""
    if not body:
        raise ToolExecutionError(message="Comment body cannot be empty.")

    client = JiraClient(context.get_auth_token_or_empty())

    adf_body = build_adf_doc(body)

    if mention_users:
        try:
            users = await find_multiple_unique_users(context, mention_users, exact_match=True)
        except (NotFoundError, MultipleItemsFoundError) as exc:
            return {"error": f"Failed to mention user: {exc.message}"}
        mentions = [
            {
                "type": "mention",
                "attrs": {"accessLevel": "", "id": user["id"], "text": f"@{user['name']}"},
            }
            for user in users
        ]
        adf_body["content"][0]["content"] = mentions + adf_body["content"][0]["content"]

    if reply_to_comment:
        quote_comment = await get_comment_by_id(context, issue, reply_to_comment, True)
        if not quote_comment["comment"]:
            raise ToolExecutionError(
                message=f"Cannot quote comment. No comment found with ID '{reply_to_comment}'."
            )
        quote = {
            "type": "blockquote",
            "content": quote_comment["comment"]["adf_body"]["content"],
        }
        adf_body["content"] = [quote] + adf_body["content"]

    response = await client.post(
        f"issue/{issue}/comment",
        json_data={
            "expand": "renderedBody",
            "body": adf_body,
        },
    )

    return {
        "success": True,
        "message": f"Comment successfully created for the issue '{issue}'.",
        "comment": {"id": response["id"], "created_at": response["created"]},
    }
