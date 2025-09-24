from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import RetryableToolError

from arcade_zendesk.enums import SortOrder, TicketStatus
from arcade_zendesk.utils import fetch_paginated_results, get_zendesk_subdomain


def _handle_ticket_not_found(response: httpx.Response, ticket_id: int) -> None:
    """Handle 404 responses for ticket operations."""
    if response.status_code == 404:
        raise RetryableToolError(
            message=f"Ticket #{ticket_id} not found.",
            developer_message=f"Ticket with ID {ticket_id} does not exist",
            retry_after_ms=500,
            additional_prompt_content="Please verify the ticket ID and try again",
        )


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def list_tickets(
    context: ToolContext,
    status: Annotated[
        TicketStatus,
        "The status of tickets to filter by. Defaults to 'open'",
    ] = TicketStatus.OPEN,
    limit: Annotated[
        int,
        "Number of tickets to return. Defaults to 30",
    ] = 30,
    offset: Annotated[
        int,
        "Number of tickets to skip before returning results. Defaults to 0",
    ] = 0,
    sort_order: Annotated[
        SortOrder,
        "Sort order for tickets by ID. 'asc' returns oldest first, 'desc' returns newest first. "
        "Defaults to 'desc'",
    ] = SortOrder.DESC,
) -> Annotated[
    dict[str, Any],
    "A dictionary containing tickets list (each with html_url), count, and pagination metadata. "
    "Includes 'next_offset' when more results are available",
]:
    """List tickets from your Zendesk account with offset-based pagination.

    By default, returns tickets sorted by ID with newest tickets first (desc).

    Each ticket in the response includes an 'html_url' field with the direct link
    to view the ticket in Zendesk.

    PAGINATION:
    - The response includes 'next_offset' when more results are available
    - To fetch the next batch, simply pass the 'next_offset' value as the 'offset' parameter
    - If 'next_offset' is not present, you've reached the end of available results
    """

    # Validate limit and offset parameters
    if limit < 1:
        raise RetryableToolError(
            message="limit must be at least 1.",
            developer_message=f"Invalid limit value: {limit}",
            retry_after_ms=100,
            additional_prompt_content="Provide a positive limit value",
        )

    if offset < 0:
        raise RetryableToolError(
            message="offset cannot be negative.",
            developer_message=f"Invalid offset value: {offset}",
            retry_after_ms=100,
            additional_prompt_content="Provide a non-negative offset value",
        )

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = get_zendesk_subdomain(context)

    # Build the API URL
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json"

    # Base parameters for the request
    base_params: dict[str, Any] = {
        "status": status.value,
        "per_page": 100,  # Max allowed per page
        "sort_order": sort_order.value,
    }

    # Make the API request
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Use the fetch_paginated_results utility
        data = await fetch_paginated_results(
            client=client,
            url=url,
            headers=headers,
            params=base_params,
            offset=offset,
            limit=limit,
        )

        # Process tickets to add html_url and remove api url
        tickets = data.get("results", [])
        for ticket in tickets:
            if "id" in ticket:
                ticket["html_url"] = f"https://{subdomain}.zendesk.com/agent/tickets/{ticket['id']}"
            # Remove API url to avoid confusion
            if "url" in ticket:
                del ticket["url"]

        # Build the result with consistent structure
        result = {
            "tickets": tickets,
            "count": data.get("count", len(tickets)),
        }

        # Add next_offset if present
        if "next_offset" in data:
            result["next_offset"] = data["next_offset"]
        return result


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def get_ticket_comments(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to get comments for"],
) -> Annotated[
    dict[str, Any], "A dictionary containing the ticket comments, metadata, and ticket URL"
]:
    """Get all comments for a specific Zendesk ticket, including the original description.

    The first comment is always the ticket's original description/content.
    Subsequent comments show the conversation history.

    Each comment includes:
    - author_id: ID of the comment author
    - body: The comment text
    - created_at: Timestamp when comment was created
    - public: Whether the comment is public or internal
    - attachments: List of file attachments (if any) with file_name, content_url, size, etc.
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = get_zendesk_subdomain(context)

    # Zendesk API endpoint for ticket comments
    url = f"https://{subdomain}.zendesk.com/api/v2/tickets/{ticket_id}/comments.json"

    # Make the API request
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await client.get(url, headers=headers)
        _handle_ticket_not_found(response, ticket_id)
        response.raise_for_status()

        data = response.json()
        comments = data.get("comments", [])

        return {
            "ticket_id": ticket_id,
            "comments": comments,
            "count": len(comments),
        }


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["tickets:write"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def add_ticket_comment(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to comment on"],
    comment_body: Annotated[str, "The text of the comment"],
    public: Annotated[
        bool, "Whether the comment is public (visible to requester) or internal. Defaults to True"
    ] = True,
) -> Annotated[
    dict[str, Any], "A dictionary containing the result of the comment operation and ticket URL"
]:
    """Add a comment to an existing Zendesk ticket.

    The returned ticket object includes an 'html_url' field with the direct link
    to view the ticket in Zendesk.
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = get_zendesk_subdomain(context)

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
        _handle_ticket_not_found(response, ticket_id)
        response.raise_for_status()

        data = response.json()
        ticket = data.get("ticket", {})

        # Add web interface URL if not present
        if "id" in ticket and "html_url" not in ticket:
            ticket["html_url"] = f"https://{subdomain}.zendesk.com/agent/tickets/{ticket['id']}"
        # Remove API url to avoid confusion
        if "url" in ticket:
            del ticket["url"]

        return {
            "success": True,
            "ticket_id": ticket_id,
            "comment_type": "public" if public else "internal",
            "ticket": ticket,
        }


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["tickets:write"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def mark_ticket_solved(
    context: ToolContext,
    ticket_id: Annotated[int, "The ID of the ticket to mark as solved"],
    comment_body: Annotated[
        str | None,
        "Optional final comment to add when solving the ticket",
    ] = None,
    comment_public: Annotated[
        bool, "Whether the comment is visible to the requester. Defaults to False"
    ] = False,
) -> Annotated[dict[str, Any], "A dictionary containing the result of the solve operation"]:
    """Mark a Zendesk ticket as solved, optionally with a final comment.

    The returned ticket object includes an 'html_url' field with the direct link
    to view the ticket in Zendesk.
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = get_zendesk_subdomain(context)

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
        _handle_ticket_not_found(response, ticket_id)
        response.raise_for_status()

        data = response.json()
        ticket = data.get("ticket", {})

        # Add web interface URL if not present
        if "id" in ticket and "html_url" not in ticket:
            ticket["html_url"] = f"https://{subdomain}.zendesk.com/agent/tickets/{ticket['id']}"
        # Remove API url to avoid confusion
        if "url" in ticket:
            del ticket["url"]

        result = {
            "success": True,
            "ticket_id": ticket_id,
            "status": "solved",
            "ticket": ticket,
        }
        if comment_body:
            result["comment_added"] = True
            result["comment_type"] = "public" if comment_public else "internal"

        return result
