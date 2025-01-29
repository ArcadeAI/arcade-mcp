"""
This example demonstrates how to get an authorization token for a user and then use it to make a request to the Google API on behalf of the user.
"""

from arcadepy import Arcade
from google.oauth2.credentials import Credentials  # pip install google-auth
from googleapiclient.discovery import build  # pip install google-api-python-client


def get_auth_token(client: Arcade, user_id: str) -> str:
    """Get an authorization token for a user.

    In this example, we are
        1. Starting the authorization process for the Gmail Readonly scope
        2. Waiting for the user to authorize the scope
        3. Getting the authorization token
        4. Using the authorization token to make a request to the Google API on behalf of the user
    """
    # Start the authorization process
    auth_response = client.auth.start(
        user_id, "google", scopes=["https://www.googleapis.com/auth/gmail.readonly"]
    )

    if auth_response.status != "completed":
        print(f"Click this link to authorize: {auth_response.url}")
        auth_response = client.auth.wait_for_completion(auth_response)

    return auth_response.context.token


def use_auth_token(token: str) -> None:
    """Use an authorization token to make a request to the Google API on behalf of a user.

    In this example, we are
        1. Using the authorization token that we got from the authorization process to make a request to the Google API
        client.auth.wait_for_completion(auth_response)
    """
    # Use the token from the authorization response
    creds = Credentials(token)
    service = build("gmail", "v1", credentials=creds)

    # Now you can use the Google API
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    print("Labels:", labels)


if __name__ == "__main__":
    cloud_host = "https://api.arcade.dev"

    client = Arcade(
        base_url=cloud_host,  # Alternatively, use http://localhost:9099 if you are running Arcade locally, or any base_url if you're hosting elsewhere
    )

    user_id = "you@example.com"

    token = get_auth_token(client, user_id)
    use_auth_token(token)
