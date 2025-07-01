from typing import Annotated, Any, Literal

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2


@tool(
    requires_auth=OAuth2(id="zendesk", scopes=["read"]),
    requires_secrets=["ZENDESK_SUBDOMAIN"],
)
async def list_tickets(
    context: ToolContext,
    status: Annotated[
        str,
        "The status of tickets to filter by (e.g., 'new', 'open', 'pending', 'solved', 'closed'). "
        "Defaults to 'open'",
    ] = "open",
    per_page: Annotated[
        int, "The number of tickets to return per page (max 100). Defaults to 100"
    ] = 100,
    page: Annotated[
        int | None,
        "The page number for offset pagination. If not provided, cursor pagination is used.",
    ] = None,
    cursor: Annotated[
        str | None,
        "The cursor for pagination. Use 'after_cursor' from previous response to get next page.",
    ] = None,
    sort_order: Annotated[
        Literal["asc", "desc"],
        "Sort order for tickets by ID. 'asc' returns oldest first, 'desc' returns newest first. "
        "Defaults to 'desc'",
    ] = "desc",
) -> Annotated[
    dict[str, Any],
    "A dictionary containing tickets list (each with html_url), count, and pagination metadata",
]:
    """List tickets from your Zendesk account with pagination support.

    By default, returns tickets sorted by ID with newest tickets first (desc).

    Each ticket in the response includes an 'html_url' field with the direct link
    to view the ticket in Zendesk.

    Supports both cursor-based pagination (recommended) and offset-based pagination.
    For cursor pagination, omit 'page' parameter and use 'cursor' for subsequent requests.
    For offset pagination, use 'page' parameter (limited to first 100 pages).
    """

    # Get the authorization token
    token = context.get_auth_token_or_empty()
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")

    if not subdomain:
        msg = "Zendesk subdomain not found in secrets. Please configure ZENDESK_SUBDOMAIN."
        raise ValueError(msg)

    # Build the API URL with query parameters
    base_url = f"https://{subdomain}.zendesk.com/api/v2/tickets.json"
    params = {"status": status}

    # Determine pagination type
    if page is not None:
        # Offset-based pagination
        params["page"] = str(page)
        params["per_page"] = str(min(per_page, 100))
        params["sort_order"] = sort_order
    else:
        # Cursor-based pagination (recommended)
        params["page[size]"] = str(min(per_page, 100))
        if cursor:
            params["page[after]"] = cursor
        # For cursor pagination, use minus sign for descending order
        params["sort"] = "-id" if sort_order == "desc" else "id"

    # Make the API request
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = await client.get(base_url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        tickets = data.get("tickets", [])

        # Build response with pagination metadata
        # Replace API url with web interface url
        for ticket in tickets:
            if "id" in ticket:
                ticket["html_url"] = f"https://{subdomain}.zendesk.com/agent/tickets/{ticket['id']}"
            # Remove API url to avoid confusion
            if "url" in ticket:
                del ticket["url"]

        result = {
            "tickets": tickets,
            "count": len(tickets),
        }

        # Add pagination metadata based on response type
        if "meta" in data:
            # Cursor-based pagination response
            result["has_more"] = data["meta"].get("has_more", False)
            result["after_cursor"] = data["meta"].get("after_cursor")
            result["before_cursor"] = data["meta"].get("before_cursor")
        else:
            # Offset-based pagination response
            result["next_page"] = data.get("next_page")
            result["previous_page"] = data.get("previous_page")
            result["total_count"] = data.get("count")

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

        if response.status_code == 404:
            msg = f"Ticket #{ticket_id} not found."
            raise ValueError(msg)

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
        "Optional final comment to add when solving (e.g., resolution summary)",
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
