from typing import Annotated

import httpx

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp


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

    url = f"https://api.github.com/user/starred/{owner}/{name}"
    authorization_header = f"Bearer {context.authorization.token}"

    async with httpx.AsyncClient() as client:
        if starred:
            response = await client.put(url, headers={"Authorization": authorization_header})
        else:
            response = await client.delete(url, headers={"Authorization": authorization_header})

    if not 200 <= response.status_code < 300:
        raise ToolExecutionError(
            f"Failed to star/unstar repository. Status code: {response.status_code}"
        )
