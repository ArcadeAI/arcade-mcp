from typing import Annotated
from arcade.sdk import tool
import requests


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
