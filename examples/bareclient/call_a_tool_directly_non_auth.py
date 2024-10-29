import os

from arcadepy import Arcade

"""
This example demonstrates how to directly call a tool that does not require authorization.
"""


def call_non_auth_tool(client, user_id):
    """Directly call a prebuilt tool that does not require authorization.

    In this example, we are
        1. Preparing the inputs to the Math.Add tool
        2. Executing the tool
        3. Printing the output of the tool's execution, i.e., the result of adding 9001 and 42

    This is a simple example of calling a non-auth tool. Next, try writing your own non-auth tool for your own use case.
    """
    # Prepare the inputs to the tool as a dictionary where keys are the names of the parameters expected by the tool and the values are the actual values to pass to the tool
    inputs = {"a": 9001, "b": 42}

    # Execute the tool
    response = client.tools.execute(
        tool_name="Math.Add",
        inputs=inputs,
        user_id=user_id,
    )

    # Print the output of the tool execution
    print(response.output.value)


if __name__ == "__main__":
    client = Arcade(
        base_url="https://api.arcade-ai.com",  # Alternatively, use http://localhost:9099 if you are running Arcade locally, or any base_url if you're hosting elsewhere
        api_key=os.environ[
            "ARCADE_API_KEY"
        ],  # Alternatively, set the API key as an environment variable and Arcade will automatically use it
    )

    user_id = "you@example.com"
    call_non_auth_tool(client, user_id)
