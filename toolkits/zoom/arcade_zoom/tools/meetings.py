from typing import Annotated, Optional

import httpx

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Zoom
from arcade.sdk.errors import ToolExecutionError

ZOOM_BASE_URL = "https://api.zoom.us/v2"


async def _send_zoom_request(
    context: ToolContext,
    method: str,
    endpoint: str,
    params: dict | None = None,
    json_data: dict | None = None,
) -> httpx.Response:
    """
    Send an asynchronous request to the Zoom API.

    Args:
        context: The tool context containing the authorization token.
        method: The HTTP method (GET, POST, PUT, DELETE, etc.).
        endpoint: The API endpoint path (e.g., "/users/me/upcoming_meetings").
        params: Query parameters to include in the request.
        json_data: JSON data to include in the request body.

    Returns:
        The response object from the API request.

    Raises:
        ToolExecutionError: If the request fails for any reason.
    """
    url = f"{ZOOM_BASE_URL}{endpoint}"
    headers = {"Authorization": f"Bearer {context.authorization.token}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method, url, headers=headers, params=params, json=json_data
            )
            response.raise_for_status()
        except httpx.RequestError as e:
            raise ToolExecutionError(f"Failed to send request to Zoom API: {e}")

    return response


def _handle_zoom_api_error(response: httpx.Response):
    """
    Handle errors from the Zoom API by mapping common status codes to ToolExecutionErrors.

    Args:
        response: The response object from the API request.

    Raises:
        ToolExecutionError: If the response contains an error status code.
    """
    status_code_map = {
        401: ToolExecutionError("Unauthorized: Invalid or expired token"),
        403: ToolExecutionError("Forbidden: Access denied"),
        429: ToolExecutionError("Too Many Requests: Rate limit exceeded"),
    }

    if response.status_code in status_code_map:
        raise status_code_map[response.status_code]
    elif response.status_code >= 400:
        raise ToolExecutionError(f"Error: {response.status_code} - {response.text}")


@tool(
    requires_auth=Zoom(
        scopes=["meeting:read:list_upcoming_meetings"],
    )
)
async def list_upcoming_meetings(
    context: ToolContext,
    user_id: Annotated[
        Optional[str],
        "The user's user ID or email address. Defaults to 'me' for the current user.",
    ] = "me",
) -> Annotated[dict, "List of upcoming meetings within the next 24 hours"]:
    """List a Zoom user's upcoming meetings within the next 24 hours."""
    endpoint = f"/users/{user_id}/upcoming_meetings"

    response = await _send_zoom_request(context, "GET", endpoint)
    if response.status_code >= 200 and response.status_code < 300:
        return response.json()
    else:
        _handle_zoom_api_error(response)


@tool(
    requires_auth=Zoom(
        scopes=["meeting:read:invitation"],
    )
)
async def get_meeting_invitation(
    context: ToolContext,
    meeting_id: Annotated[
        str,
        "The meeting's numeric ID (as a string).",
    ],
) -> Annotated[dict, "Meeting invitation string"]:
    """Retrieve the invitation note for a specific Zoom meeting."""
    endpoint = f"/meetings/{meeting_id}/invitation"

    response = await _send_zoom_request(context, "GET", endpoint)
    if response.status_code >= 200 and response.status_code < 300:
        return response.json()
    else:
        _handle_zoom_api_error(response)
