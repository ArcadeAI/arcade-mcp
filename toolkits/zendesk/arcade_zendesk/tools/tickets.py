from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def list_tickets(
    context: ToolContext,
) -> Annotated[dict[str, Any], "A dictionary containing the list of tickets and count"]:
    """List open tickets from your Zendesk account."""

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")

    if not subdomain:
        msg = "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        raise ValueError(msg)

    # Zendesk API endpoint for tickets
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json?status=open"

    # Make the API request
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            tickets = data.get("tickets", [])

            # Return structured data
            return {
                "tickets": tickets,
                "count": len(tickets)
            }
        else:
            msg = f"Error fetching tickets: {response.status_code} - {response.text}"
            raise ValueError(msg)


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def get_ticket_comments(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to get comments for"],
) -> Annotated[
    dict[str, Any], "A dictionary containing the ticket comments and metadata"
]:
    """Get all comments for a specific Zendesk ticket, including the original description.

    The first comment is always the ticket's original description/content.
    Subsequent comments show the conversation history.
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")

    if not subdomain:
        msg = "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        raise ValueError(msg)

    # Zendesk API endpoint for ticket comments
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}/comments.json"

    # Make the API request
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await client.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            comments = data.get("comments", [])

            return {
                "ticket_id": ticket_id,
                "comments": comments,
                "count": len(comments)
            }
        elif response.status_code == 404:
            msg = f"Ticket #{ticket_id} not found."
            raise ValueError(msg)
        else:
            msg = f"Error fetching comments: {response.status_code} - {response.text}"
            raise ValueError(msg)


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["tickets:write"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def add_ticket_comment(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to comment on"],
    comment_body: Annotated[str, "The text of the comment"],
    public: Annotated[
        bool, "Whether the comment is public (visible to requester) or internal"
    ] = True,
) -> Annotated[
    dict[str, Any], "A dictionary containing the result of the comment operation"
]:
    """Add a comment to an existing Zendesk ticket.

    Args:
        ticket_id: The ID of the ticket to comment on
        comment_body: The text of the comment
        public: Whether the comment is public (visible to requester) or internal
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")

    if not subdomain:
        msg = "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        raise ValueError(msg)

    # Zendesk API endpoint for updating ticket
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}.json"

    # Prepare the request body
    request_body = {"ticket": {"comment": {"body": comment_body, "public": public}}}

    # Make the API request
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await client.put(url, headers=headers, json=request_body)

        if response.status_code == 200:
            data = response.json()
            ticket = data.get("ticket", {})
            return {
                "success": True,
                "ticket_id": ticket_id,
                "comment_type": "public" if public else "internal",
                "ticket": ticket
            }
        else:
            error_data = (
                response.json()
                if response.headers.get("content-type") == "application/json"
                else {}
            )
            error_message = error_data.get("error", response.text)
            msg = f"Error adding comment to ticket: {response.status_code} - {error_message}"
            raise ValueError(msg)


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["tickets:write"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def mark_ticket_solved(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to mark as solved"],
    comment_body: Annotated[
        str | None,
        "Optional final comment to add when solving (e.g., resolution summary)",
    ] = None,
    comment_public: Annotated[bool, "Whether the comment is visible to the requester"] = False,
) -> Annotated[
    dict[str, Any], "A dictionary containing the result of the solve operation"
]:
    """Mark a Zendesk ticket as solved, optionally with a final comment.

    Args:
        ticket_id: The ID of the ticket to mark as solved
        comment_body: Optional final comment to add when solving (e.g., resolution summary)
        comment_public: Whether the comment is visible to the requester (default False - internal)
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")

    if not subdomain:
        msg = "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        raise ValueError(msg)

    # Zendesk API endpoint for updating ticket
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}.json"

    # Prepare the request body
    request_body: dict[str, Any] = {"ticket": {"status": "solved"}}

    # Add resolution comment if provided
    if comment_body:
        request_body["ticket"]["comment"] = {
            "body": comment_body,
            "public": comment_public,
        }

    # Make the API request
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await client.put(url, headers=headers, json=request_body)

        if response.status_code == 200:
            data = response.json()
            ticket = data.get("ticket", {})
            result = {
                "success": True,
                "ticket_id": ticket_id,
                "status": "solved",
                "ticket": ticket
            }
            if comment_body:
                result["comment_added"] = True
                result["comment_type"] = "public" if comment_public else "internal"
            return result
        else:
            error_data = (
                response.json()
                if response.headers.get("content-type") == "application/json"
                else {}
            )
            error_message = error_data.get("error", response.text)
            msg = f"Error marking ticket as solved: {response.status_code} - {error_message}"
            raise ValueError(msg)
