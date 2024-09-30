import json
from typing import Annotated, Optional

import httpx

from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp
from arcade_github.tools.models import (
    PRSortProperty,
    PRState,
    ReviewCommentSortProperty,
    SortDirection,
)
from arcade_github.tools.utils import (
    get_github_headers,
    get_url,
    handle_github_response,
    remove_none_values,
)


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
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
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
    url = get_url("repo_pulls", owner=owner, repo=repo)
    params = {
        "base": base,
        "state": state.value,
        "sort": sort.value,
        "per_page": min(max(1, per_page), 100),  # clamp per_page to 1-100
        "page": page,
        "head": head,
        "direction": direction,  # Note: Github defaults to desc when sort is 'created' or not specified, otherwise defaults to asc
    }
    params = remove_none_values(params)
    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    handle_github_response(response, url)

    pull_requests = response.json()
    results = []
    for pr in pull_requests:
        if include_extra_data:
            results.append(pr)
            continue
        results.append({
            "number": pr.get("number"),
            "title": pr.get("title"),
            "body": pr.get("body"),
            "state": pr.get("state"),
            "html_url": pr.get("html_url"),
            "diff_url": pr.get("diff_url"),
            "created_at": pr.get("created_at"),
            "updated_at": pr.get("updated_at"),
            "user": pr.get("user", {}).get("login"),
            "base": pr.get("base", {}).get("ref"),
            "head": pr.get("head", {}).get("ref"),
        })
    return json.dumps({"pull_requests": results})


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
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
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
    url = get_url("repo_pull", owner=owner, repo=repo, pull_number=pull_number)
    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    handle_github_response(response, url)

    pr_data = response.json()
    if include_extra_data:
        return json.dumps(pr_data)
    important_info = {
        "number": pr_data.get("number"),
        "title": pr_data.get("title"),
        "body": pr_data.get("body"),
        "state": pr_data.get("state"),
        "html_url": pr_data.get("html_url"),
        "diff_url": pr_data.get("diff_url"),
        "created_at": pr_data.get("created_at"),
        "updated_at": pr_data.get("updated_at"),
        "user": pr_data.get("user", {}).get("login"),
        "base": pr_data.get("base", {}).get("ref"),
        "head": pr_data.get("head", {}).get("ref"),
    }
    return json.dumps(important_info)


# Example arcade chat usage: Get PR 72 in ArcadeAI/arcade-ai, then update PR 72 in ArcadeAI/arcade-ai by adding "This portion of the PR description was added via arcade chat!" to the end of the body/description
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
    url = get_url("repo_pull", owner=owner, repo=repo, pull_number=pull_number)

    data = {
        "title": title,
        "body": body,
        "state": state.value if state else None,
        "base": base,
        "maintainer_can_modify": maintainer_can_modify,
    }
    data = remove_none_values(data)

    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.patch(url, headers=headers, json=data)

    handle_github_response(response, url)

    pr_data = response.json()
    important_info = {
        "url": pr_data.get("url"),
        "id": pr_data.get("id"),
        "html_url": pr_data.get("html_url"),
        "number": pr_data.get("number"),
        "state": pr_data.get("state"),
        "title": pr_data.get("title"),
        "user": pr_data.get("user", {}).get("login"),
        "body": pr_data.get("body"),
        "created_at": pr_data.get("created_at"),
        "updated_at": pr_data.get("updated_at"),
    }
    return json.dumps(important_info)


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
    url = get_url("repo_pull_commits", owner=owner, repo=repo, pull_number=pull_number)

    params = {
        "per_page": max(1, min(100, per_page)),  # clamp per_page to 1-100
        "page": page,
    }

    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    handle_github_response(response, url)

    commits = response.json()
    return json.dumps({"commits": commits})


# This tool requires the ID of the review comment to reply to, which can be found by calling list_review_comments_on_pull_request
# Example arcade chat usage: "create a reply to the review comment 1778019974 in arcadeai/arcade-ai for the pull request number 72 that says 'Thanks for the suggestion.'"
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
    create_reply_for_review_comment(owner="octocat", repo="Hello-World", pull_number=1347, comment_id=42, body="Looks good to me!")
    ```
    """
    # Implements https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#create-a-reply-for-a-review-comment
    url = get_url(
        "repo_pull_comment_replies",
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        comment_id=comment_id,
    )

    headers = get_github_headers(context.authorization.token)

    data = {"body": body}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)

    handle_github_response(response, url)

    return json.dumps(response.json())


# Example arcade chat usage: "list all of the review comments for PR 72 in arcadeai/arcade-ai"
@tool(requires_auth=GitHubApp())
async def list_review_comments_on_pull_request(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    pull_number: Annotated[int, "The number that identifies the pull request."],
    sort: Annotated[
        Optional[ReviewCommentSortProperty],
        "The property to sort the results by. Can be one of: created, updated.",
    ] = ReviewCommentSortProperty.CREATED,
    direction: Annotated[
        Optional[SortDirection], "The direction to sort results. Can be one of: asc, desc."
    ] = SortDirection.DESC,
    since: Annotated[
        Optional[str],
        "Only show results that were last updated after the given time. This is a timestamp in ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ.",
    ] = None,
    per_page: Annotated[Optional[int], "The number of results per page (max 100)."] = 30,
    page: Annotated[Optional[int], "The page number of the results to fetch."] = 1,
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> str:
    """
    List review comments on a pull request in a GitHub repository.

    Example:
    ```
    list_review_comments_on_pull_request(owner="octocat", repo="Hello-World", pull_number=1347)
    ```
    """
    # Implements: https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#create-a-review-comment-for-a-pull-request
    url = get_url("repo_pull_comments", owner=owner, repo=repo, pull_number=pull_number)

    params = {
        "sort": sort,
        "direction": direction,
        "per_page": max(1, min(100, per_page)),  # clamp per_page to 1-100
        "page": page,
        "since": since,
    }
    params = remove_none_values(params)

    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    handle_github_response(response, url)

    review_comments = response.json()
    if include_extra_data:
        return json.dumps(review_comments)

    filtered_comments = []
    for comment in review_comments:
        filtered_comment = {
            "id": comment.get("id"),
            "url": comment.get("url"),
            "diff_hunk": comment.get("diff_hunk"),
            "path": comment.get("path"),
            "position": comment.get("position"),
            "original_position": comment.get("original_position"),
            "commit_id": comment.get("commit_id"),
            "original_commit_id": comment.get("original_commit_id"),
            "in_reply_to_id": comment.get("in_reply_to_id"),
            "user": comment.get("user", {}).get("login"),
            "body": comment.get("body"),
            "created_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "html_url": comment.get("html_url"),
            "line": comment.get("line"),
            "side": comment.get("side"),
            "pull_request_url": comment.get("pull_request_url"),
        }
        filtered_comments.append(filtered_comment)
    return json.dumps({"review_comments": filtered_comments})
