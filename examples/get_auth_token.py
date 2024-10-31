"""
This example demonstrates how to get an authorization token for a user and then use it to make a request to the Google API on behalf of the user.
"""

import os

from arcadepy import Arcade
from arcadepy.types.auth_authorize_params import (
    AuthRequirement,
    AuthRequirementOauth2,
)
from google.oauth2.credentials import Credentials  # pip install google-auth
from googleapiclient.discovery import build  # pip install google-api-python-client


def get_auth_token(client, user_id):
    """Get an authorization token for a user.

    In this example, we are
        1. Starting the authorization process for the Gmail Readonly scope
        2. Waiting for the user to authorize the scope
        3. Getting the authorization token
        4. Using the authorization token to make a request to the Google API on behalf of the user
    """
    # Start the authorization process
    auth_response = client.auth.authorize(
        auth_requirement=AuthRequirement(
            provider_id="google",
            oauth2=AuthRequirementOauth2(
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            ),
        ),
        user_id=user_id,
    )

    if auth_response.status != "completed":
        print(f"Click this link to authorize: {auth_response.authorization_url}")
        client.auth.wait_for_completion(auth_response.id)

    return auth_response.context.token


def use_auth_token(token):
    """Use an authorization token to make a request to the Google API on behalf of a user.

    In this example, we are
        1. Using the authorization token that we got from the authorization process to make a request to the Google API
        2. Printing the response from the Google API
    """
    # Use the token from the authorization response
    creds = Credentials(token)
    service = build("gmail", "v1", credentials=creds)

    # Now you can use the Google API
    results = service.users().labels().list(userId="me").execute()
    labels = results.get("labels", [])
    print("Labels:", labels)


if __name__ == "__main__":
    arcade_api_key = os.environ[
        "ARCADE_API_KEY"
    ]  # If you forget your arcade API key, it is stored at ~/.arcade/credentials.yaml on `arcade login`
    cloud_host = "https://api.arcade-ai.com"

    client = Arcade(
        base_url=cloud_host,  # Alternatively, use http://localhost:9099 if you are running Arcade locally, or any base_url if you're hosting elsewhere
        api_key=arcade_api_key,
    )

    user_id = "you@example.com"

    token = get_auth_token(client, user_id)
    use_auth_token(token)
