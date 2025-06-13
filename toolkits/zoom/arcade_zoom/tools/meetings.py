from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Zoom

from arcade_zoom.tools.utils import _handle_zoom_api_error, _send_zoom_request


@tool(
    requires_auth=Zoom(
        scopes=["meeting:read:list_upcoming_meetings"],
    )
)
async def list_upcoming_meetings(
    context: ToolContext,
    user_id: Annotated[
        str | None,
        "The user's user ID or email address. Defaults to 'me' for the current user.",
    ] = "me",
) -> Annotated[dict, "List of upcoming meetings within the next 24 hours"]:
    """List a Zoom user's upcoming meetings within the next 24 hours."""
    endpoint = f"/users/{user_id}/upcoming_meetings"

    response = await _send_zoom_request(context, "GET", endpoint)

    if not (200 <= response.status_code < 300):
        _handle_zoom_api_error(response)

    response_json = response.json()
    return dict(response_json)


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

    if not (200 <= response.status_code < 300):
        _handle_zoom_api_error(response)

    response_json = response.json()
    return dict(response_json)
