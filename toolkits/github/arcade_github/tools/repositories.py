import json
from typing import Annotated, Optional

import httpx

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import GitHub
from arcade_github.tools.models import (
    ActivityType,
    RepoSortProperty,
    RepoTimePeriod,
    RepoType,
    ReviewCommentSortProperty,
    SortDirection,
)
from arcade_github.tools.utils import (
    get_github_json_headers,
    get_url,
    handle_github_response,
    remove_none_values,
)


# Implements https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository and returns only the stargazers_count field.
# Example arcade chat usage: "How many stargazers does the <OWNER>/<REPO> repo have?"
@tool(requires_auth=GitHub())
async def count_stargazers(
    context: ToolContext,
    owner: Annotated[str, "The owner of the repository"],
    name: Annotated[str, "The name of the repository"],
) -> Annotated[int, "The number of stargazers (stars) for the specified repository"]:
    """Count the number of stargazers (stars) for a GitHub repository.
    For example, to count the number of stars for microsoft/vscode, you would use:
    ```
    count_stargazers(owner="microsoft", name="vscode")
    ```
    """

    headers = get_github_json_headers(context.authorization.token)

    url = get_url("repo", owner=owner, repo=name)
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    handle_github_response(response, url)

    data = response.json()
    stargazers_count = data.get("stargazers_count", 0)
    return stargazers_count


# Implements https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-organization-repositories
# Example arcade chat usage: "List all repositories for the <ORG> organization. Sort by creation date in descending order."
@tool(requires_auth=GitHub())
async def list_org_repositories(
    context: ToolContext,
    org: Annotated[str, "The organization name. The name is not case sensitive"],
    repo_type: Annotated[RepoType, "The types of repositories you want returned."] = RepoType.ALL,
    sort: Annotated[
        RepoSortProperty, "The property to sort the results by"
    ] = RepoSortProperty.CREATED,
    sort_direction: Annotated[SortDirection, "The order to sort by"] = SortDirection.ASC,
    per_page: Annotated[Optional[int], "The number of results per page"] = 30,
    page: Annotated[Optional[int], "The page number of the results to fetch"] = 1,
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> Annotated[
    dict[str, list[dict]],
    "A dictionary with key 'repositories' containing a list of repositories, each with details such as name, full_name, html_url, description, clone_url, private status, creation/update/push timestamps, and star/watcher/fork counts",
]:
    """List repositories for the specified organization."""
    url = get_url("org_repos", org=org)
    params = {
        "type": repo_type.value,
        "sort": sort.value,
        "direction": sort_direction.value,
        "per_page": per_page,
        "page": page,
    }

    headers = get_github_json_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    handle_github_response(response, url)

    repos = response.json()
    if include_extra_data:
        return {"repositories": repos}

    results = []
    for repo in repos:
        results.append({
            "name": repo["name"],
            "full_name": repo["full_name"],
            "html_url": repo["html_url"],
            "description": repo["description"],
            "clone_url": repo["clone_url"],
            "private": repo["private"],
            "created_at": repo["created_at"],
            "updated_at": repo["updated_at"],
            "pushed_at": repo["pushed_at"],
            "stargazers_count": repo["stargazers_count"],
            "watchers_count": repo["watchers_count"],
            "forks_count": repo["forks_count"],
        })

    return {"repositories": results}


# Implements https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
# Example arcade chat usage: "Tell me about the <OWNER>/<REPO> repo."
@tool(requires_auth=GitHub())
async def get_repository(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> Annotated[
    dict,
    "A dictionary containing repository details such as name, full_name, html_url, description, clone_url, private status, creation/update/push timestamps, and star/watcher/fork counts",
]:
    """Get a repository.

    Retrieves detailed information about a repository using the GitHub API.

    Example:
    ```
    get_repository(owner="octocat", repo="Hello-World")
    ```
    """
    url = get_url("repo", owner=owner, repo=repo)
    headers = get_github_json_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    handle_github_response(response, url)

    repo_data = response.json()
    if include_extra_data:
        return json.dumps(repo_data)

    return {
        "name": repo_data["name"],
        "full_name": repo_data["full_name"],
        "html_url": repo_data["html_url"],
        "description": repo_data["description"],
        "clone_url": repo_data["clone_url"],
        "private": repo_data["private"],
        "created_at": repo_data["created_at"],
        "updated_at": repo_data["updated_at"],
        "pushed_at": repo_data["pushed_at"],
        "stargazers_count": repo_data["stargazers_count"],
        "watchers_count": repo_data["watchers_count"],
        "forks_count": repo_data["forks_count"],
    }


# Implements https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-repository-activities
# Example arcade chat usage: "List all merges into main for the <OWNER>/<REPO> repo in the last week by <USER>"
@tool(requires_auth=GitHub())
async def list_repository_activities(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    direction: Annotated[
        Optional[SortDirection], "The direction to sort the results by."
    ] = SortDirection.DESC,
    per_page: Annotated[Optional[int], "The number of results per page (max 100)."] = 30,
    before: Annotated[
        Optional[str],
        "A cursor (unique identifier, e.g., a SHA of a commit) to search for results before this cursor.",
    ] = None,
    after: Annotated[
        Optional[str],
        "A cursor (unique identifier, e.g., a SHA of a commit) to search for results after this cursor.",
    ] = None,
    ref: Annotated[
        Optional[str],
        "The Git reference for the activities you want to list. The ref for a branch can be formatted either as refs/heads/BRANCH_NAME or BRANCH_NAME, where BRANCH_NAME is the name of your branch.",
    ] = None,
    actor: Annotated[
        Optional[str], "The GitHub username to filter by the actor who performed the activity."
    ] = None,
    time_period: Annotated[Optional[RepoTimePeriod], "The time period to filter by."] = None,
    activity_type: Annotated[Optional[ActivityType], "The activity type to filter by."] = None,
    include_extra_data: Annotated[
        bool,
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> Annotated[
    str,
    "A JSON string containing a dictionary with key 'activities', which is a list of repository activities. Each activity includes id, node_id, before and after states, ref, timestamp, activity_type, and actor information",
]:
    """List repository activities.

    Retrieves a detailed history of changes to a repository, such as pushes, merges, force pushes, and branch changes,
    and associates these changes with commits and users.

    Example:
    ```
    list_repository_activities(
        owner="octocat",
        repo="Hello-World",
        per_page=10,
        activity_type="force_push"
    )
    ```
    """
    url = get_url("repo_activity", owner=owner, repo=repo)
    params = {
        "direction": direction.value,
        "per_page": min(100, per_page),  # The API only allows up to 100 per page
        "before": before,
        "after": after,
        "ref": ref,
        "actor": actor,
        "time_period": time_period,
        "activity_type": activity_type,
    }
    params = remove_none_values(params)

    headers = get_github_json_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    handle_github_response(response, url)

    activities = response.json()
    if include_extra_data:
        return json.dumps({"activities": activities})

    results = []
    for activity in activities:
        results.append({
            "id": activity["id"],
            "node_id": activity["node_id"],
            "before": activity.get("before"),
            "after": activity.get("after"),
            "ref": activity.get("ref"),
            "timestamp": activity.get("timestamp"),
            "activity_type": activity.get("activity_type"),
            "actor": activity.get("actor", {}).get("login") if activity.get("actor") else None,
        })
    return json.dumps({"activities": results})


# Implements https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#list-review-comments-in-a-repository
# Example arcade chat usage: "List all review comments for the <OWNER>/<REPO> repo. Sort by update date in descending order."
# TODO: Improve the 'since' input parameter such that language model can more easily specify a valid date/time.
@tool(requires_auth=GitHub())
async def list_review_comments_in_a_repository(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    sort: Annotated[
        Optional[ReviewCommentSortProperty], "Can be one of: created, updated."
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
        "If true, return all the data available about the pull requests. This is a large payload and may impact performance - use with caution.",
    ] = False,
) -> Annotated[
    str,
    "A JSON string containing a dictionary with key 'review_comments', which is a list of review comments. Each comment includes id, url, diff_hunk, path, position details, commit information, user, body, timestamps, and related URLs",
]:
    """
    List review comments in a GitHub repository.

    Example:
    ```
    list_review_comments(owner="octocat", repo="Hello-World", sort="created", direction="asc")
    ```
    """
    url = get_url("repo_pulls_comments", owner=owner, repo=repo)

    params = {
        "per_page": min(max(1, per_page), 100),  # clamp per_page to 1-100
        "page": page,
        "sort": sort,
        "direction": direction,
        "since": since,
    }
    params = remove_none_values(params)
    headers = get_github_json_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    handle_github_response(response, url)

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
