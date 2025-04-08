"""
This example demonstrates how to directly call a tool that requires a secret such as an API key.

For this example, we will use the Web.ScrapeUrl tool which requires the FIRECRAWL_API_KEY secret.
The FIRECRAWL_API_KEY secret is a static secret that all Arcade Cloud users have access to.

To view or add more secrets, go to https://api.arcade.dev/dashboard/auth/secrets
"""

import os

from arcadepy import Arcade  # pip install arcade-py


def call_an_api_key_tool(client: Arcade, user_id: str) -> None:
    """Directly call a tool that requires an API key.

    In this example, we are
        1. Preparing the inputs to the Web.ScrapeUrl tool
        2. Executing the tool
        3. Printing the output of the tool's execution which is a URL to a screenshot of the page at https://docs.arcade.dev/home/quickstart

    This is an example of calling a tool that requires an API key. Next, try writing your own tool that requires an API key for your own use case.
    """
    # Prepare the inputs to the tool as a dictionary where keys are the names of the parameters expected by the tool and the values are the actual values to pass to the tool
    tool_input = {
        "url": "https://docs.arcade.dev/home/quickstart",
        "formats": [
            "screenshot@fullPage"
        ],  # Other options include "markdown", "html", "rawHtml", "links", "screenshot"
        "wait_for": 250,  # Give the page 250ms to load
    }

    # Execute the tool
    response = client.tools.execute(
        tool_name="Web.ScrapeUrl",  # this tool uses the FIRECRAWL_API_KEY secret. To view or add more secrets, go to https://api.arcade.dev/dashboard/auth/secrets
        input=tool_input,
        user_id=user_id,
    )

    # Print the output of the tool execution
    print(response.output.value["screenshot"])


if __name__ == "__main__":
    client = Arcade(
        base_url="https://api.arcade.dev",  # Alternatively, use http://localhost:9099 if you are running Arcade Engine locally, or any base_url if you're hosting elsewhere
        api_key=os.environ[
            "ARCADE_API_KEY"
        ],  # Alternatively, set the API key as an environment variable and Arcade will automatically use it
    )
    user_id = "you@example.com"

    call_an_api_key_tool(client, user_id)
