import json
from typing import Annotated, Optional

import httpx

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp
from arcade_github.tools.models import RepoSortDirection, RepoSortProperty, RepoType


@tool(requires_auth=GitHubApp())
async def search_issues(
    context: ToolContext,
    owner: Annotated[str, "The owner of the repository"],
    name: Annotated[str, "The name of the repository"],
    query: Annotated[str, "The query to search for"],
    limit: Annotated[int, "The maximum number of issues to return"] = 10,
) -> dict[str, list[dict]]:
    """Search for issues in a GitHub repository."""

    # Build the search query
    url = f"https://api.github.com/search/issues?q={query}+is:issue+is:open+repo:{owner}/{name}+sort:created-desc&per_page={limit}"

    # Make the API request
    headers = {
        "Authorization": f"token {context.authorization.token}",
        "Accept": "application/vnd.github.v3+json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    # Check for successful response
    # handle 422 for can't find repo
    # TODO - how should errors bubble back up if tool_choice=execute
    if response.status_code != 200:
        raise ToolExecutionError(f"Failed to fetch issues: {response.status_code}")

    issues = response.json().get("items", [])
    results = []
    for issue in issues:
        results.append({
            "title": issue["title"],
            "url": issue["html_url"],
            "created_at": issue["created_at"],
        })

    return {"issues": results}


# TODO: This does not support private repositories. https://app.clickup.com/t/86b1r3mhe
@tool
async def count_stargazers(
    owner: Annotated[str, "The owner of the repository"],
    name: Annotated[str, "The name of the repository"],
) -> int:
    """Count the number of stargazers (stars) for a public GitHub repository.
    For example, to count the number of stars for microsoft/vscode, you would use:
    ```
    count_stargazers(owner="microsoft", name="vscode")
    ```
    """

    url = f"https://api.github.com/repos/{owner}/{name}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)

    print(response)

    if response.status_code == 200:
        data = response.json()
        return data.get("stargazers_count", 0)
    else:
        raise ToolExecutionError(
            f"Failed to fetch repository data. Status code: {response.status_code}"
        )


@tool(requires_auth=GitHubApp())
async def list_org_repositories(
    context: ToolContext,
    org: Annotated[str, "The organization name. The name is not case sensitive"],
    repo_type: Annotated[RepoType, "The types of repositories you want returned."] = RepoType.ALL,
    sort: Annotated[
        RepoSortProperty, "The property to sort the results by"
    ] = RepoSortProperty.CREATED,
    sort_direction: Annotated[RepoSortDirection, "The order to sort by"] = RepoSortDirection.ASC,
    per_page: Annotated[Optional[int], "The number of results per page"] = 30,
    page: Annotated[Optional[int], "The page number of the results to fetch"] = 1,
    return_all: Annotated[bool, "If true, return all the data about all the repositories"] = False,
) -> dict[str, list[dict]]:
    """List repositories for the specified organization."""
    # Implements https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#list-organization-repositories
    url = f"https://api.github.com/orgs/{org}/repos"
    params = {
        "type": repo_type.value,
        "sort": sort.value,
        "direction": sort_direction.value,
        "per_page": per_page,
        "page": page,
    }

    headers = {
        "Authorization": f"token {context.authorization.token}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise ToolExecutionError(f"Failed to fetch repositories: {response.status_code}")

    repos = response.json()
    if return_all:
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


@tool(requires_auth=GitHubApp())
async def get_repository(
    context: ToolContext,
    owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
    repo: Annotated[
        str,
        "The name of the repository without the .git extension. The name is not case sensitive.",
    ],
    return_all: Annotated[bool, "If true, return all the data about the repository"] = False,
) -> dict:
    """Get a repository.

    Retrieves detailed information about a repository using the GitHub API.

    Example:
    ```
    get_repository(owner="octocat", repo="Hello-World")
    ```
    """
    # Implements https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {context.authorization.token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)

    if response.status_code == 200:
        repo_data = response.json()
        if return_all:
            return json.dumps(repo_data)
        else:
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
    elif response.status_code == 301:
        raise ToolExecutionError(
            "Failed to fetch repository data. Moved permanently. The repository has moved."
        )
    elif response.status_code == 403:
        raise ToolExecutionError(
            "Failed to fetch repository data. Forbidden. You do not have access to this repository."
        )
    elif response.status_code == 404:
        raise ToolExecutionError(
            "Failed to fetch repository data. Resource not found. The repository does not exist."
        )
    else:
        raise ToolExecutionError(
            f"Failed to fetch repository data. Status code: {response.status_code}"
        )


# @tool(requires_auth=GitHubApp())
# async def list_repository_activities(
#     context: ToolContext,
#     owner: Annotated[str, "The account owner of the repository. The name is not case sensitive."],
#     repo: Annotated[
#         str,
#         "The name of the repository without the .git extension. The name is not case sensitive.",
#     ],
#     direction: Annotated[
#         Optional[RepoSortDirection], "The direction to sort the results by."
#     ] = RepoSortDirection.DESC,
#     per_page: Annotated[Optional[int], "The number of results per page (max 100)."] = 30,
#     before: Annotated[Optional[str], "A cursor to search for results before this cursor."] = None,
#     after: Annotated[Optional[str], "A cursor to search for results after this cursor."] = None,
#     ref: Annotated[Optional[str], "The Git reference for the activities you want to list."] = None,
#     actor: Annotated[
#         Optional[str], "The GitHub username to filter by the actor who performed the activity."
#     ] = None,
#     time_period: Annotated[Optional[str], "The time period to filter by."] = None,
#     activity_type: Annotated[Optional[str], "The activity type to filter by."] = None,
#     return_all: Annotated[bool, "If true, return all the data about the activities."] = False,
# ) -> dict[str, list[dict]]:
#     """List repository activities.

#     Retrieves a detailed history of changes to a repository, such as pushes, merges, force pushes, and branch changes,
#     and associates these changes with commits and users.

#     Example:
#     ```
#     list_repository_activities(
#         owner="octocat",
#         repo="Hello-World",
#         per_page=10,
#         activity_type="force_push"
#     )
#     ```
#     """
#     url = f"https://api.github.com/repos/{owner}/{repo}/activity"
#     params = {
#         "direction": direction.value,
#         "per_page": per_page,
#     }

#     if before:
#         params["before"] = before
#     if after:
#         params["after"] = after
#     if ref:
#         params["ref"] = ref
#     if actor:
#         params["actor"] = actor
#     if time_period:
#         params["time_period"] = time_period
#     if activity_type:
#         params["activity_type"] = activity_type

#     headers = {
#         "Accept": "application/vnd.github+json",
#         "Authorization": f"Bearer {context.authorization.token}",
#         "X-GitHub-Api-Version": "2022-11-28",
#     }

#     async with httpx.AsyncClient() as client:
#         response = await client.get(url, headers=headers, params=params)

#     if response.status_code == 200:
#         activities = response.json()
#         if return_all:
#             return {"activities": activities}

#         results = []
#         for activity in activities:
#             results.append({
#                 "id": activity["id"],
#                 "node_id": activity["node_id"],
#                 "before": activity.get("before"),
#                 "after": activity.get("after"),
#                 "ref": activity.get("ref"),
#                 "timestamp": activity.get("timestamp"),
#                 "activity_type": activity.get("activity_type"),
#                 "actor": activity.get("actor", {}).get("login") if activity.get("actor") else None,
#             })
#         return {"activities": results}
#     elif response.status_code == 422:
#         raise ToolExecutionError("Validation failed or the endpoint has been spammed.")
#     else:
#         raise ToolExecutionError(
#             f"Failed to fetch repository activities. Status code: {response.status_code}"
#         )
