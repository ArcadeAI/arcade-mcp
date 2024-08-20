from typing import Annotated
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import GitHubApp
import requests


@tool(requires_auth=GitHubApp())
def set_starred(
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
    response = (
        requests.put(url, headers={"Authorization": authorization_header})
        if starred
        else requests.delete(url, headers={"Authorization": authorization_header})
    )

    if not 200 <= response.status_code < 300:
        raise Exception(
            f"Failed to star/unstar repository. Status code: {response.status_code}"
        )
