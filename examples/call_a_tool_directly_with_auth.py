"""
This example demonstrates how to directly call a tool that requires authorization.
"""

from arcadepy import Arcade  # pip install arcade-py


def call_auth_tool(client: Arcade, user_id: str) -> None:
    """Directly call a prebuilt tool that requires authorization.

    In this example, we are
        1. Authorizing Arcade to read emails from the user's Gmail account with the user's permission to do so
        2. Reading 5 emails from the user's Gmail account
        3. Printing the emails

    Try altering this example to call a tool that requires a different authorization.
    """
    # Start the authorization process
    auth_response = client.tools.authorize(
        tool_name="Google.ListEmails",
        user_id=user_id,
    )

    # If not already authorized, then wait for the user to authorize the permissions required by the tool
    if auth_response.status != "completed":
        print(f"Click this link to authorize: {auth_response.url}")

    # Wait for the user to complete the auth flow, if necessary
    client.auth.wait_for_completion(auth_response)

    # Prepare the inputs to the tool as a dictionary where keys are the names of the parameters expected by the tool and the values are the actual values to pass to the tool
    tool_input = {"n_emails": 5}

    # Execute the tool
    response = client.tools.execute(
        tool_name="Google.ListEmails",
        input=tool_input,
        user_id=user_id,
    )

    # Print the output of the tool execution.
    print(response)


if __name__ == "__main__":
    client = Arcade(
        base_url="https://api.arcade.dev",  # Alternatively, use http://localhost:9099 if you are running Arcade Engine locally, or any base_url if you're hosting elsewhere
    )

    user_id = "you@example.com"
    call_auth_tool(client, user_id)
