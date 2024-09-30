import json
from typing import Annotated, Optional

import httpx

from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp
from arcade_github.tools.utils import (
    get_github_headers,
    get_url,
    handle_github_response,
    remove_none_values,
)


@tool(requires_auth=GitHubApp())
async def create_issue(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    title: Annotated[str, "The title of the issue."],
    body: Annotated[Optional[str], "The contents of the issue."] = None,
    assignees: Annotated[Optional[list[str]], "Logins for Users to assign to this issue."] = None,
    milestone: Annotated[
        Optional[int], "The number of the milestone to associate this issue with."
    ] = None,
    labels: Annotated[Optional[list[str]], "Labels to associate with this issue."] = None,
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> str:
    """
    Create an issue in a GitHub repository.

    Example:
    ```
    create_issue(owner="octocat", repo="Hello-World", title="Found a bug", body="I'm having a problem with this.", assignees=["octocat"], milestone=1, labels=["bug"])
    ```
    """
    # Implements https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#create-an-issue
    url = get_url("repo_issues", owner=owner, repo=repo)
    data = {
        "title": title,
        "body": body,
        "labels": labels,
        "milestone": milestone,
        "assignees": assignees,
    }
    data = remove_none_values(data)
    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)

    handle_github_response(response, url)

    issue_data = response.json()
    if include_extra_data:
        return json.dumps(issue_data)

    important_info = {
        "id": issue_data.get("id"),
        "url": issue_data.get("url"),
        "title": issue_data.get("title"),
        "body": issue_data.get("body"),
        "state": issue_data.get("state"),
        "html_url": issue_data.get("html_url"),
        "created_at": issue_data.get("created_at"),
        "updated_at": issue_data.get("updated_at"),
        "user": issue_data.get("user", {}).get("login"),
        "assignees": [assignee.get("login") for assignee in issue_data.get("assignees", [])],
        "labels": [label.get("name") for label in issue_data.get("labels", [])],
    }
    return json.dumps(important_info)


@tool(requires_auth=GitHubApp())
async def create_issue_comment(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    issue_number: Annotated[int, "The number that identifies the issue."],
    body: Annotated[str, "The contents of the comment."],
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> str:
    """
    Create a comment on an issue in a GitHub repository.

    Example:
    ```
    create_issue_comment(owner="octocat", repo="Hello-World", issue_number=1347, body="Me too")
    ```
    """
    # Implements https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#create-an-issue-comment
    url = get_url("repo_issue_comments", owner=owner, repo=repo, issue_number=issue_number)
    data = {
        "body": body,
    }
    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)

    handle_github_response(response, url)

    comment_data = response.json()
    if include_extra_data:
        return json.dumps(comment_data)

    important_info = {
        "id": comment_data.get("id"),
        "url": comment_data.get("url"),
        "body": comment_data.get("body"),
        "user": comment_data.get("user", {}).get("login"),
        "created_at": comment_data.get("created_at"),
        "updated_at": comment_data.get("updated_at"),
    }
    return json.dumps(important_info)
