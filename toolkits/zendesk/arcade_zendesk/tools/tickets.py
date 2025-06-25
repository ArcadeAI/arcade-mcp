from typing import Annotated, Any, Optional

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def list_tickets(context: ToolContext) -> Annotated[str, "The tickets"]:
    """List open tickets from your Zendesk account."""

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")

    if not subdomain:
        raise ValueError(
            "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        )

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

            # Format the tickets for display
            if not tickets:
                return "No open tickets found."

            result = []
            for ticket in tickets:
                ticket_info = (
                    f"Ticket #{ticket['id']}: {ticket['subject']} (Status: {ticket['status']})"
                )
                result.append(ticket_info)

            return "\n".join(result)
        else:
            return f"Error fetching tickets: {response.status_code} - {response.text}"


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def get_ticket_comments(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to get comments for"],
) -> Annotated[str, "The ticket comments including the original description"]:
    """Get all comments for a specific Zendesk ticket, including the original description.

    The first comment is always the ticket's original description/content.
    Subsequent comments show the conversation history.
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")

    if not subdomain:
        raise ValueError(
            "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        )

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

            if not comments:
                return f"No comments found for ticket #{ticket_id}."

            result = [f"Comments for Ticket #{ticket_id}:\n"]

            for i, comment in enumerate(comments):
                author_id = comment.get("author_id", "Unknown")
                created_at = comment.get("created_at", "Unknown time")
                body = comment.get("body", "No content")
                public = comment.get("public", True)

                # Format the comment
                if i == 0:
                    result.append("=== Original Description ===")
                else:
                    comment_type = "Public" if public else "Internal"
                    result.append(f"\n=== Comment #{i} ({comment_type}) ===")

                result.append(f"Author ID: {author_id}")
                result.append(f"Created: {created_at}")
                result.append(f"Content: {body}")

            return "\n".join(result)
        elif response.status_code == 404:
            return f"Ticket #{ticket_id} not found."
        else:
            return f"Error fetching comments: {response.status_code} - {response.text}"


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
) -> Annotated[str, "Result of adding comment to ticket"]:
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
        raise ValueError(
            "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        )

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
            comment_type = "public" if public else "internal"
            return f"Successfully added {comment_type} comment to ticket #{ticket_id}"
        else:
            error_data = (
                response.json()
                if response.headers.get("content-type") == "application/json"
                else {}
            )
            error_message = error_data.get("error", response.text)
            return f"Error adding comment to ticket: {response.status_code} - {error_message}"


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["tickets:write"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def mark_ticket_solved(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to mark as solved"],
    comment_body: Annotated[
        Optional[str],
        "Optional final comment to add when solving (e.g., resolution summary)",
    ] = None,
    comment_public: Annotated[bool, "Whether the comment is visible to the requester"] = False,
) -> Annotated[str, "Result of marking ticket as solved"]:
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
        raise ValueError(
            "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        )

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
            message = f"Successfully marked ticket #{ticket_id} as solved"
            if comment_body:
                comment_type = "public" if comment_public else "internal"
                message += f" with {comment_type} resolution comment"

            return message
        else:
            error_data = (
                response.json()
                if response.headers.get("content-type") == "application/json"
                else {}
            )
            error_message = error_data.get("error", response.text)
            return f"Error marking ticket as solved: {response.status_code} - {error_message}"
