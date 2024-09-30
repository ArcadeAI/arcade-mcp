from typing import Annotated, Optional

import requests

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import OAuth2


@tool(
    requires_auth=OAuth2(
        provider_id="zoom",
        authority="https://zoom.us",
        scopes=["meeting:read:list_upcoming_meetings"],
    )
)
def list_upcoming_meetings(
    context: ToolContext,
    user_id: Annotated[
        Optional[str],
        "The user's user ID or email address. Defaults to 'me' for the current user.",
    ] = "me",
) -> Annotated[dict, "List of upcoming meetings within the next 24 hours"]:
    """List a Zoom user's upcoming meetings within the next 24 hours."""
    url = f"https://api.zoom.us/v2/users/{user_id}/upcoming_meetings"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}

    try:
        response = requests.get(url, headers=headers)
    except Exception as e:
        raise ToolExecutionError(f"Failed to list upcoming meetings: {e}")

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        raise ToolExecutionError("Unauthorized: Invalid or expired token")
    elif response.status_code == 403:
        raise ToolExecutionError("Forbidden: Access denied")
    elif response.status_code == 429:
        raise ToolExecutionError("Too Many Requests: Rate limit exceeded")
    else:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")


@tool(
    requires_auth=OAuth2(
        provider_id="zoom",
        authority="https://zoom.us",
        scopes=["meeting:read:invitation"],
    )
)
def get_meeting_invitation(
    context: ToolContext,
    meeting_id: Annotated[
        str,
        "The meeting's numeric ID (as a string).",
    ],
) -> Annotated[dict, "Meeting invitation string"]:
    """Retrieve the invitation note for a specific Zoom meeting."""
    url = f"https://api.zoom.us/v2/meetings/{meeting_id}/invitation"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}

    try:
        response = requests.get(url, headers=headers)
    except Exception as e:
        raise ToolExecutionError(f"Failed to retrieve meeting invitation: {e}")

    if response.status_code == 200:
        return response.json()
    elif response.status_code == 401:
        raise ToolExecutionError("Unauthorized: Invalid or expired token")
    elif response.status_code == 403:
        raise ToolExecutionError("Forbidden: Access denied")
    elif response.status_code == 429:
        raise ToolExecutionError("Too Many Requests: Rate limit exceeded")
    else:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")
