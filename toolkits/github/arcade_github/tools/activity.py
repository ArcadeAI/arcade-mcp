from typing import Annotated

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import GitHub

from arcade_github.tools.utils import get_github_json_headers, get_url, handle_github_response


# Implements https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#star-a-repository-for-the-authenticated-user and https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#unstar-a-repository-for-the-authenticated-user  # noqa: E501
# Example `arcade chat` usage: "star the vscode repo owned by microsoft"
@tool(requires_auth=GitHub())
async def set_starred(
    context: ToolContext,
    owner: Annotated[str, "The owner of the repository"],
    name: Annotated[str, "The name of the repository"],
    starred: Annotated[bool, "Whether to star the repository or not"] = True,
) -> Annotated[
    str, "A message indicating whether the repository was successfully starred or unstarred"
]:
    """
    Star or un-star a GitHub repository.
    For example, to star microsoft/vscode, you would use:
    ```
    set_starred(owner="microsoft", name="vscode", starred=True)
    ```
    """
    url = get_url("user_starred", owner=owner, repo=name)
    headers = get_github_json_headers(
        context.authorization.token if context.authorization and context.authorization.token else ""
    )

    async with httpx.AsyncClient() as client:
        if starred:
            response = await client.put(url, headers=headers)
        else:
            response = await client.delete(url, headers=headers)

    handle_github_response(response, url)

    action = "starred" if starred else "unstarred"
    return f"Successfully {action} the repository {owner}/{name}"


# Implements https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#list-stargazers
# Example `arcade chat` usage: "list the stargazers for the ArcadeAI/arcade-ai repo"
@tool(requires_auth=GitHub())
async def list_stargazers(
    context: ToolContext,
    owner: Annotated[str, "The owner of the repository"],
    repo: Annotated[str, "The name of the repository"],
    limit: Annotated[
        int | None,
        "The maximum number of stargazers to return. "
        "If not provided, all stargazers will be returned.",
    ] = None,
) -> Annotated[dict, "A dictionary containing the stargazers for the specified repository"]:
    """List the stargazers for a GitHub repository."""
    url = get_url("repo_stargazers", owner=owner, repo=repo)
    headers = get_github_json_headers(
        context.authorization.token if context.authorization and context.authorization.token else ""
    )

    if limit is None:
        limit = 2**64 - 1

    per_page = min(limit, 100)
    page = 1
    stargazers: list[dict] = []

    async with httpx.AsyncClient() as client:
        while len(stargazers) < limit:
            response = await client.get(
                url, headers=headers, params={"per_page": per_page, "page": page}
            )
            handle_github_response(response, url)

            data = response.json()
            if not data:
                break

            stargazers.extend([
                {
                    "login": stargazer.get("login"),
                    "id": stargazer.get("id"),
                    "node_id": stargazer.get("node_id"),
                    "html_url": stargazer.get("html_url"),
                }
                for stargazer in data
            ])

            if len(data) < per_page:
                break

            page += 1

    stargazers = stargazers[:limit]
    return {"number_of_stargazers": len(stargazers), "stargazers": stargazers}
