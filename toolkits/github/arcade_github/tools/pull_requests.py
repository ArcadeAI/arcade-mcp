import json
from enum import Enum
from typing import Annotated, Optional

import httpx

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp
from arcade_github.tools.models import PRSortProperty, ReviewCommentSortProperty, SortDirection


class PRState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


# Example arcade chat usage: "get all open PRs that EricGustin has that are in the ArcadeAI/arcade-ai repo"
@tool(requires_auth=GitHubApp())
async def list_pull_requests(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    state: Annotated[Optional[PRState], "The state of the pull requests to return."] = PRState.OPEN,
    head: Annotated[
        Optional[str],
        "Filter pulls by head user or head organization and branch name in the format of user:ref-name or organization:ref-name.",
    ] = None,
    base: Annotated[Optional[str], "Filter pulls by base branch name."] = "main",
    sort: Annotated[
        Optional[PRSortProperty], "The property to sort the results by."
    ] = PRSortProperty.CREATED,
    direction: Annotated[Optional[SortDirection], "The direction of the sort."] = None,
    per_page: Annotated[Optional[int], "The number of results per page (max 100)."] = 30,
    page: Annotated[Optional[int], "The page number of the results to fetch."] = 1,
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use sparingly.",
    ] = False,
) -> str:
    """
    List pull requests in a GitHub repository.

    Example:
    ```
    list_pull_requests(owner="octocat", repo="Hello-World", state=PRState.OPEN, sort=PRSort.UPDATED)
    ```
    """
    # Implements https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests

    # TODO: Validate owner/repo combination is valid for the authenticated user
    # TODO: list repo's branches and validate base is in the list (or default to main)
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"

    params = {
        "base": base,
        "state": state.value,
        "sort": sort.value,
        "per_page": max(1, min(100, per_page)),  # clamp per_page to 1-100
        "page": page,
    }

    if head:
        params["head"] = head
    if direction:
        # Github defaults to desc when sort is created or sort is not specified, otherwise Github defaults to asc
        params["direction"] = direction.value

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.authorization.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code == 200:
        pull_requests = response.json()
        results = []
        for pr in pull_requests:
            if include_extra_data:
                results.append(pr)
            else:
                results.append({
                    "number": pr["number"],
                    "title": pr["title"],
                    "body": pr["body"],
                    "state": pr["state"],
                    "html_url": pr["html_url"],
                    "diff_url": pr["diff_url"],
                    "created_at": pr["created_at"],
                    "updated_at": pr["updated_at"],
                    "user": pr["user"]["login"],
                    "base": pr["base"]["ref"],
                    "head": pr["head"]["ref"],
                })
        return json.dumps({"pull_requests": results})
    elif response.status_code == 304:
        return json.dumps({"pull_requests": []})
    elif response.status_code == 422:
        raise ToolExecutionError(f"Validation failed or the endpoint '{url}' has been spammed.")
    else:
        raise ToolExecutionError(
            f"Failed to fetch pull requests from '{url}'. Status code: {response.status_code}"
        )


@tool(requires_auth=GitHubApp())
async def get_pull_request(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    pull_number: Annotated[int, "The number that identifies the pull request."],
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use sparingly.",
    ] = False,
) -> str:
    """
    Get details of a pull request in a GitHub repository.

    Example:
    ```
    get_pull_request(owner="octocat", repo="Hello-World", pull_number=1347)
    ```
    """
    # Implements https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.authorization.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 200:
        pr_data = response.json()
        if include_extra_data:
            return json.dumps(pr_data)
        else:
            important_info = {
                "number": pr_data["number"],
                "title": pr_data["title"],
                "body": pr_data["body"],
                "state": pr_data["state"],
                "html_url": pr_data["html_url"],
                "diff_url": pr_data["diff_url"],
                "created_at": pr_data["created_at"],
                "updated_at": pr_data["updated_at"],
                "user": pr_data["user"]["login"],
                "base": pr_data["base"]["ref"],
                "head": pr_data["head"]["ref"],
            }
            return json.dumps(important_info)
    elif response.status_code == 404:
        raise ToolExecutionError(f"Pull request not found at '{url}'.")
    elif response.status_code == 406:
        raise ToolExecutionError(f"Unacceptable request to '{url}'.")
    elif response.status_code == 500:
        raise ToolExecutionError(f"Internal server error at '{url}'.")
    elif response.status_code == 503:
        raise ToolExecutionError(f"Service unavailable at '{url}'.")
    else:
        raise ToolExecutionError(
            f"Failed to fetch pull request from '{url}'. Status code: {response.status_code}"
        )


# Get PR 72 in ArcadeAI/arcade-ai, thenupdate PR 72 in ArcadeAI/arcade-ai by adding "This portion of the PR description was added via arcade chat!" to the end of the body/description
@tool(requires_auth=GitHubApp())
async def update_pull_request(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    pull_number: Annotated[int, "The number that identifies the pull request."],
    title: Annotated[Optional[str], "The title of the pull request."] = None,
    body: Annotated[Optional[str], "The contents of the pull request."] = None,
    state: Annotated[
        Optional[PRState], "State of this Pull Request. Either open or closed."
    ] = None,
    base: Annotated[
        Optional[str], "The name of the branch you want your changes pulled into."
    ] = None,
    maintainer_can_modify: Annotated[
        Optional[bool], "Indicates whether maintainers can modify the pull request."
    ] = None,
) -> str:
    """
    Update a pull request in a GitHub repository.

    Example:
    ```
    update_pull_request(owner="octocat", repo="Hello-World", pull_number=1347, title="new title", body="updated body")
    ```
    """
    # Implements https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#update-a-pull-request

    # TODO: force "get PR" tool to be called first so that the user can append/alter PR contents instead of just replacing them.
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"

    data = {}
    if title:
        data["title"] = title
    if body:
        data["body"] = body
    if state:
        data["state"] = state.value
    if base:
        data["base"] = base
    if maintainer_can_modify:
        data["maintainer_can_modify"] = maintainer_can_modify

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.authorization.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=data)

    if response.status_code == 200:
        pr_data = response.json()
        important_info = {
            "url": pr_data["url"],
            "id": pr_data["id"],
            "html_url": pr_data["html_url"],
            "number": pr_data["number"],
            "state": pr_data["state"],
            "title": pr_data["title"],
            "user": pr_data["user"]["login"],
            "body": pr_data["body"],
            "created_at": pr_data["created_at"],
            "updated_at": pr_data["updated_at"],
        }
        return json.dumps(important_info)
    elif response.status_code == 403:
        raise ToolExecutionError(
            f"Forbidden. You do not have access to update this pull request at {url}."
        )
    elif response.status_code == 422:
        raise ToolExecutionError(f"Validation failed or the endpoint '{url}' has been spammed.")
    else:
        raise ToolExecutionError(
            f"Failed to update pull request at {url}. Status code: {response.status_code}"
        )


# Example arcade chat usage: "list all of the commits for the pull request number 72 in arcadeai/arcade-ai"
@tool(requires_auth=GitHubApp())
async def list_pull_request_commits(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    pull_number: Annotated[int, "The number that identifies the pull request."],
    per_page: Annotated[Optional[int], "The number of results per page (max 100)."] = 30,
    page: Annotated[Optional[int], "The page number of the results to fetch."] = 1,
) -> str:
    """
    List commits on a pull request in a GitHub repository.

    Example:
    ```
    list_pull_request_commits(owner="octocat", repo="Hello-World", pull_number=1347)
    ```
    """
    # Implements https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-commits-on-a-pull-request
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/commits"

    params = {
        "per_page": max(1, min(100, per_page)),  # clamp per_page to 1-100
        "page": page,
    }

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.authorization.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise ToolExecutionError(
            f"Failed to fetch commits from '{url}'. Status code: {response.status_code}"
        )

    commits = response.json()
    return json.dumps({"commits": commits})


@tool(requires_auth=GitHubApp())
async def list_review_comments(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    sort: Annotated[
        Optional[ReviewCommentSortProperty], "Can be one of: created, updated, created_at."
    ] = ReviewCommentSortProperty.CREATED,
    direction: Annotated[
        Optional[SortDirection],
        "The direction to sort results. Ignored without sort parameter. Can be one of: asc, desc.",
    ] = SortDirection.DESC,
    since: Annotated[
        Optional[str],
        "Only show results that were last updated after the given time. This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.",
    ] = None,
    per_page: Annotated[Optional[int], "The number of results per page (max 100)."] = 30,
    page: Annotated[Optional[int], "The page number of the results to fetch."] = 1,
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use sparingly.",
    ] = False,
) -> str:
    """
    List review comments in a GitHub repository.

    Example:
    ```
    list_review_comments(owner="octocat", repo="Hello-World", sort="created", direction="asc")
    ```
    """
    # Implements https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#list-review-comments-in-a-repository
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/comments"

    params = {
        "per_page": max(1, min(100, per_page)),  # clamp per_page to 1-100
        "page": page,
    }

    if sort:
        params["sort"] = sort
    if direction:
        params["direction"] = direction
    if since:
        params["since"] = since

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.authorization.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code == 200:
        review_comments = response.json()
        if include_extra_data:
            return json.dumps({"review_comments": review_comments})
        else:
            important_info = [
                {
                    "id": comment["id"],
                    "url": comment["url"],
                    "diff_hunk": comment["diff_hunk"],
                    "path": comment["path"],
                    "position": comment["position"],
                    "original_position": comment["original_position"],
                    "commit_id": comment["commit_id"],
                    "original_commit_id": comment["original_commit_id"],
                    "in_reply_to_id": comment.get("in_reply_to_id"),
                    "user": comment["user"]["login"],
                    "body": comment["body"],
                    "created_at": comment["created_at"],
                    "updated_at": comment["updated_at"],
                    "html_url": comment["html_url"],
                    "line": comment["line"],
                    "side": comment["side"],
                    "pull_request_url": comment["pull_request_url"],
                }
                for comment in review_comments
            ]
            return json.dumps({"review_comments": important_info})
    else:
        raise ToolExecutionError(
            f"Failed to fetch review comments from '{url}'. Status code: {response.status_code}"
        )


@tool(requires_auth=GitHubApp())
async def create_reply_for_review_comment(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    pull_number: Annotated[int, "The number that identifies the pull request."],
    comment_id: Annotated[int, "The unique identifier of the comment."],
    body: Annotated[str, "The text of the review comment."],
) -> str:
    """
    Create a reply to a review comment for a pull request.

    Example:
    ```
    create_reply_for_review_comment(owner="octocat", repo="Hello-World", pull_number=1347, comment_id=42, body="Great stuff!")
    ```
    """
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}/comments/{comment_id}/replies"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.authorization.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    data = {"body": body}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)

    if response.status_code == 201:
        return response.json()
    elif response.status_code == 404:
        raise ToolExecutionError(f"Resource not found at '{url}'.")
    else:
        raise ToolExecutionError(
            f"Failed to create reply for review comment at '{url}'. Status code: {response.status_code}"
        )
