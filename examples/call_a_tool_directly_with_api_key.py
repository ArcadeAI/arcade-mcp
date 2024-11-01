"""
This example demonstrates how to directly call a tool that requires an API key.
"""

import os

from arcade_web.tools.models import Formats  # pip install arcade-web
from arcadepy import Arcade  # pip install arcade-py


def call_an_api_key_tool(client, user_id):
    """Directly call a tool that requires an API key.

    In this example, we are
        1. Preparing the inputs to the Web.ScrapeUrl tool
        2. Executing the tool
        3. Printing the output of the tool's execution, i.e., a URL to a screenshot of the page at https://arcade-ai.com

    This is an example of calling a tool that requires an API key. Next, try writing your own tool that requires an API key for your own use case.
    """
    # Prepare the inputs to the tool as a dictionary where keys are the names of the parameters expected by the tool and the values are the actual values to pass to the tool
    inputs = {
        "url": "https://docs.arcade-ai.com/home",
        "formats": [
            Formats.SCREENSHOT
        ],  # Other options include Formats.MARKDOWN, Formats.HTML, Formats.RAW_HTML, Formats.LINKS
        "wait_for": 250,
    }

    # Execute the tool
    response = client.tools.execute(
        tool_name="Web.ScrapeUrl",  # Ensure your FIRECRAWL_API_KEY environment variable is set
        inputs=inputs,
        user_id=user_id,
    )

    # Print the output of the tool execution
    print(response.output.value["screenshot"])


if __name__ == "__main__":
    client = Arcade(
        base_url="https://api.arcade-ai.com",  # Alternatively, use http://localhost:9099 if you are running Arcade Engine locally, or any base_url if you're hosting elsewhere
        api_key=os.environ[
            "ARCADE_API_KEY"
        ],  # Alternatively, set the API key as an environment variable and Arcade will automatically use it
    )
    user_id = "you@example.com"

    call_an_api_key_tool(client, user_id)
