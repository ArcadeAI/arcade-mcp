from typing import Annotated

import httpx

from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp
from arcade_github.tools.utils import get_github_headers, get_url, handle_github_response


@tool(requires_auth=GitHubApp())
async def set_starred(
    context: ToolContext,
    owner: Annotated[str, "The owner of the repository"],
    name: Annotated[str, "The name of the repository"],
    starred: Annotated[bool, "Whether to star the repository or not"],
):
    """
    Star or un-star a GitHub repository.
    For example, to star microsoft/vscode, you would use:
    ```
    set_starred(owner="microsoft", name="vscode", starred=True)
    ```
    """
    # Implements https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#star-a-repository-for-the-authenticated-user
    # and https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28#unstar-a-repository-for-the-authenticated-user
    url = get_url("user_starred", owner=owner, repo=name)
    headers = get_github_headers(context.authorization.token)

    async with httpx.AsyncClient() as client:
        if starred:
            response = await client.put(url, headers=headers)
        else:
            response = await client.delete(url, headers=headers)

    handle_github_response(response, url)

    return "Successfully " + "un" * (not starred) + "starred the repository " + owner + "/" + name
