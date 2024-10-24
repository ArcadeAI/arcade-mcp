import json
from typing import Annotated, Optional

import httpx

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import GitHub
from arcade.sdk.errors import RetryableToolError
from arcade_github.tools.models import (
    DiffSide,
    PRSortProperty,
    PRState,
    ReviewCommentSortProperty,
    ReviewCommentSubjectType,
    SortDirection,
)
from arcade_github.tools.utils import (
    get_github_diff_headers,
    get_github_json_headers,
    get_url,
    handle_github_response,
    remove_none_values,
)


# Implements https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests
# Example `arcade chat` usage: "get all open PRs that <USER> has that are in the <OWNER>/<REPO> repo"
# TODO: Validate owner/repo combination is valid for the authenticated user. If not, return RetryableToolError with available repos.
# TODO: list repo's branches and validate base is in the list (or default to main). If not, return RetryableToolError with available branches.
@tool(requires_auth=GitHub())
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
) -> Annotated[str, "JSON string containing a list of pull requests with their details"]:
    """
    List pull requests in a GitHub repository.

    Example:
    ```
    list_pull_requests(owner="octocat", repo="Hello-World", state=PRState.OPEN, sort=PRSort.UPDATED)
    ```
    """
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
    headers = get_github_json_headers(context.authorization.token)

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


# Implements https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request
# Example `arcade chat` usage: "get the PR #72 in the <OWNER>/<REPO> repo. Include diff content in your response."
@tool(requires_auth=GitHub())
async def get_pull_request(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    pull_number: Annotated[int, "The number that identifies the pull request."],
    include_diff_content: Annotated[
        Optional[bool],
        "If true, return the diff content of the pull request.",
    ] = False,
    include_extra_data: Annotated[
        Optional[bool],
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> Annotated[
    str,
    "JSON string containing details of the specified pull request, optionally including diff content",
]:
    """
    Get details of a pull request in a GitHub repository.

    Example:
    ```
    get_pull_request(owner="octocat", repo="Hello-World", pull_number=1347)
    ```
    """
    url = get_url("repo_pull", owner=owner, repo=repo, pull_number=pull_number)
    headers = get_github_json_headers(context.authorization.token)
    diff_headers = get_github_diff_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if include_diff_content:
            diff_response = await client.get(url, headers=diff_headers)

    handle_github_response(response, url)

    if include_diff_content:
        handle_github_response(diff_response, url)

    pr_data = response.json()

    if include_extra_data:
        result = pr_data
        if include_diff_content:
            result["diff_content"] = diff_response.content.decode("utf-8")
        return json.dumps(result)

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

    if include_diff_content:
        important_info["diff_content"] = diff_response.content.decode("utf-8")

    return json.dumps(important_info)


# Implements https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#update-a-pull-request
# Example `arcade chat` usage: "update PR #72 in the <OWNER>/<REPO> repo by changing the title to 'New Title' and setting the body to 'This PR description was added via arcade chat!'."
# TODO: Enable this tool to append to the PR contents instead of only replacing content.
@tool(requires_auth=GitHub())
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
) -> Annotated[str, "JSON string containing updated information about the pull request"]:
    """
    Update a pull request in a GitHub repository.

    Example:
    ```
    update_pull_request(owner="octocat", repo="Hello-World", pull_number=1347, title="new title", body="updated body")
    ```
    """
    url = get_url("repo_pull", owner=owner, repo=repo, pull_number=pull_number)

    data = {
        "title": title,
        "body": body,
        "state": state.value if state else None,
        "base": base,
        "maintainer_can_modify": maintainer_can_modify,
    }
    data = remove_none_values(data)

    headers = get_github_json_headers(context.authorization.token)

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


# Implements https://docs.github.com/en/rest/pulls/commits?apiVersion=2022-11-28#list-commits-on-a-pull-request
# Example `arcade chat` usage: "list all of the commits for the PR 72 in the <OWNER>/<REPO> repo"
@tool(requires_auth=GitHub())
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
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> Annotated[str, "JSON string containing a list of commits for the specified pull request"]:
    """
    List commits (from oldest to newest) on a pull request in a GitHub repository.

    Example:
    ```
    list_pull_request_commits(owner="octocat", repo="Hello-World", pull_number=1347)
    ```
    """
    url = get_url("repo_pull_commits", owner=owner, repo=repo, pull_number=pull_number)

    params = {
        "per_page": max(1, min(100, per_page)),  # clamp per_page to 1-100
        "page": page,
    }

    headers = get_github_json_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    handle_github_response(response, url)

    commits = response.json()
    if include_extra_data:
        return json.dumps({"commits": commits})

    filtered_commits = []
    for commit in commits:
        filtered_commit = {
            "sha": commit.get("sha"),
            "html_url": commit.get("html_url"),
            "diff_url": commit.get("html_url") + ".diff" if commit.get("html_url") else None,
            "commit": {
                "message": commit.get("commit", {}).get("message"),
                "author": commit.get("commit", {}).get("author", {}).get("name"),
                "committer": commit.get("commit", {}).get("committer", {}).get("name"),
                "date": commit.get("commit", {}).get("committer", {}).get("date"),
            },
            "author": commit.get("author", {}).get("login"),
            "committer": commit.get("committer", {}).get("login"),
        }
        filtered_commits.append(filtered_commit)

    return json.dumps({"commits": filtered_commits})


# Implements https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#create-a-reply-for-a-review-comment
# Example `arcade chat` usage: "create a reply to the review comment 1778019974 in arcadeai/arcade-ai for the PR 72 that says 'Thanks for the suggestion.'"
# Note: This tool requires the ID of the review comment to reply to. To obtain this ID, you should first call the `list_review_comments_on_pull_request` function.
#       The returned JSON will contain the `id` field for each comment, which can be used as the `comment_id` parameter in this function.
@tool(requires_auth=GitHub())
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
) -> Annotated[str, "JSON string containing details of the created reply comment"]:
    """
    Create a reply to a review comment for a pull request.

    Example:
    ```
    create_reply_for_review_comment(owner="octocat", repo="Hello-World", pull_number=1347, comment_id=42, body="Looks good to me!")
    ```
    """
    url = get_url(
        "repo_pull_comment_replies",
        owner=owner,
        repo=repo,
        pull_number=pull_number,
        comment_id=comment_id,
    )

    headers = get_github_json_headers(context.authorization.token)

    data = {"body": body}

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=data)

    handle_github_response(response, url)

    return json.dumps(response.json())


# Implements https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#list-review-comments-on-a-pull-request
# Example `arcade chat` usage: "list all of the review comments for PR 72 in <OWNER>/<REPO>"
@tool(requires_auth=GitHub())
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
) -> Annotated[
    str, "JSON string containing a list of review comments for the specified pull request"
]:
    """
    List review comments on a pull request in a GitHub repository.

    Example:
    ```
    list_review_comments_on_pull_request(owner="octocat", repo="Hello-World", pull_number=1347)
    ```
    """
    url = get_url("repo_pull_comments", owner=owner, repo=repo, pull_number=pull_number)

    params = {
        "sort": sort,
        "direction": direction,
        "per_page": max(1, min(100, per_page)),  # clamp per_page to 1-100
        "page": page,
        "since": since,
    }
    params = remove_none_values(params)

    headers = get_github_json_headers(context.authorization.token)

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


# Implements https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#create-a-review-comment-for-a-pull-request
# Example `arcade chat` usage: "create a review comment for PR 72 in <OWNER>/<REPO> that says 'Great stuff! This looks good to merge. Add the comment to README.md file.'"
# TODO: Verify that path parameter exists in the PR's files that have changed (Or should we allow for any file in the repo?). If not, then throw RetryableToolError with all valid file paths.
@tool(requires_auth=GitHub())
async def create_review_comment(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    pull_number: Annotated[int, "The number that identifies the pull request."],
    body: Annotated[str, "The text of the review comment."],
    path: Annotated[str, "The relative path to the file that necessitates a comment."],
    commit_id: Annotated[
        Optional[str],
        "The SHA of the commit needing a comment. If not provided, the latest commit SHA of the PR's base branch will be used.",
    ] = None,
    start_line: Annotated[
        Optional[int],
        "The start line of the range of lines in the pull request diff that the comment applies to. Required unless 'subject_type' is 'file'.",
    ] = None,
    end_line: Annotated[
        Optional[int],
        "The end line of the range of lines in the pull request diff that the comment applies to. Required unless 'subject_type' is 'file'.",
    ] = None,
    side: Annotated[
        Optional[DiffSide],
        "The side of the diff that the pull request's changes appear on. Use LEFT for deletions that appear in red. Use RIGHT for additions that appear in green or unchanged lines that appear in white and are shown for context",
    ] = DiffSide.RIGHT,
    start_side: Annotated[
        Optional[str], "The starting side of the diff that the comment applies to."
    ] = None,
    subject_type: Annotated[
        Optional[ReviewCommentSubjectType],
        "The type of subject that the comment applies to. Can be one of: file, hunk, or line.",
    ] = ReviewCommentSubjectType.FILE,
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the review comment. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> Annotated[str, "JSON string containing details of the created review comment"]:
    """
    Create a review comment for a pull request in a GitHub repository.

    If the subject_type is not 'file', then the start_line and end_line parameters are required.
    If the subject_type is 'file', then the start_line and end_line parameters are ignored.
    If the commit_id is not provided, the latest commit SHA of the PR's base branch will be used.

    Example:
    ```
    create_review_comment(owner="octocat", repo="Hello-World", pull_number=1347, body="Great stuff!", commit_id="6dcb09b5b57875f334f61aebed695e2e4193db5e", path="file1.txt", line=2, side="RIGHT")
    ```
    """
    # If the subject_type is 'file', then the line_range parameter is ignored
    if subject_type == ReviewCommentSubjectType.FILE:
        start_line, end_line = None, None

    if (start_line is None or end_line is None) and subject_type != ReviewCommentSubjectType.FILE:
        raise RetryableToolError(
            "'start_line' and 'end_line' parameters are required when 'subject_type' parameter is not 'file'. Either provide both a start_line and end_line or set subject_type to 'file'."
        )

    # Ensure the line range goes from lowest to highest
    if start_line is not None and end_line is not None:
        start_line, end_line = (min(start_line, end_line), max(start_line, end_line))

    # Get the latest commit SHA of the PR's base branch and use that for the commit_id
    if not commit_id:
        commits_json = await list_pull_request_commits(context, owner, repo, pull_number)
        commits_data = json.loads(commits_json)
        commits = commits_data.get("commits", [])
        latest_commit = commits[-1] if commits else {}
        commit_id = latest_commit.get("sha")

    if not commit_id:
        raise RetryableToolError(
            f"Failed to get the latest commit SHA of PR {pull_number} in repo {repo} owned by {owner}. Does the PR exist?"
        )

    url = get_url("repo_pull_comments", owner=owner, repo=repo, pull_number=pull_number)
    data = {
        "body": body,
        "commit_id": commit_id,
        "path": path,
        "side": side,
        "line": end_line if end_line else None,
        "start_line": start_line
        if start_line and start_line != end_line
        else None,  # Only send start_line when using multi-line comments
        "start_side": start_side,
    }
    data = remove_none_values(data)
    headers = get_github_json_headers(context.authorization.token)

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
        "path": comment_data.get("path"),
        "line": comment_data.get("line"),
        "side": comment_data.get("side"),
        "commit_id": comment_data.get("commit_id"),
        "user": comment_data.get("user", {}).get("login"),
        "created_at": comment_data.get("created_at"),
        "updated_at": comment_data.get("updated_at"),
        "html_url": comment_data.get("html_url"),
    }
    return json.dumps(important_info)
