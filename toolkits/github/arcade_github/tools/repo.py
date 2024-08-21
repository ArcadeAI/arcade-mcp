from typing import Annotated
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp
import requests


@tool(requires_auth=GitHubApp())
def search_issues(
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

    response = requests.get(url, headers=headers)

    # Check for successful response
    # handle 422 for can't find repo
    # TODO - how should errors bubble back up if tool_choice=execute
    if response.status_code != 200:
        raise Exception(f"Failed to fetch issues: {response.status_code}")

    issues = response.json().get("items", [])
    results = []
    for issue in issues:
        results.append(
            {
                "title": issue["title"],
                "url": issue["html_url"],
                "created_at": issue["created_at"],
            }
        )

    return {"issues": results}


# TODO: This does not support private repositories. https://app.clickup.com/t/86b1r3mhe
@tool
def count_stargazers(
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
    response = requests.get(url)

    print(response)

    if response.status_code == 200:
        data = response.json()
        return data.get("stargazers_count", 0)
    else:
        raise Exception(
            f"Failed to fetch repository data. Status code: {response.status_code}"
        )
