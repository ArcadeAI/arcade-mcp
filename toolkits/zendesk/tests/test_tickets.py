from unittest.mock import MagicMock

import httpx
import pytest
from arcade_core.errors import ToolExecutionError

from arcade_zendesk.tools.tickets import (
    add_ticket_comment,
    get_ticket_comments,
    list_tickets,
    mark_ticket_solved,
)


class TestListTickets:
    """Test list_tickets functionality."""

    @pytest.mark.asyncio
    async def test_list_tickets_success(self, mock_context, mock_httpx_client, mock_http_response):
        """Test successful listing of open tickets."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock response data - includes url field that should be removed
        tickets_response = {
            "tickets": [
                {
                    "id": 1,
                    "subject": "Login issue",
                    "status": "open",
                    "url": "https://test-subdomain.zendesk.com/api/v2/tickets/1.json",
                },
                {
                    "id": 2,
                    "subject": "Password reset request",
                    "status": "open",
                    "url": "https://test-subdomain.zendesk.com/api/v2/tickets/2.json",
                },
            ]
        }

        mock_httpx_client.get.return_value = mock_http_response(tickets_response)

        result = await list_tickets(mock_context)

        # Verify the result is structured data
        assert isinstance(result, dict)
        assert "tickets" in result
        assert "count" in result
        assert result["count"] == 2

        # Verify tickets have html_url but not url
        for ticket in result["tickets"]:
            assert "url" not in ticket
            assert "html_url" in ticket
            assert ticket["html_url"].startswith("https://test-subdomain.zendesk.com/agent/tickets/")

        # Verify the API call with default parameters
        mock_httpx_client.get.assert_called_once()
        call_args = mock_httpx_client.get.call_args
        assert call_args[0][0] == "https://test-subdomain.zendesk.com/api/v2/tickets.json"
        assert call_args[1]["params"]["status"] == "open"
        assert call_args[1]["params"]["page[size]"] == "100"  # Default per_page
        assert call_args[1]["params"]["sort"] == "-id"  # Default sort_order desc

    @pytest.mark.asyncio
    async def test_list_tickets_with_pagination(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test listing tickets with pagination parameters."""
        mock_context.get_secret.return_value = "test-subdomain"

        tickets_response = {
            "tickets": [{"id": 1, "subject": "Test", "status": "open"}],
            "meta": {"has_more": True, "after_cursor": "abc123"},
        }

        mock_httpx_client.get.return_value = mock_http_response(tickets_response)

        result = await list_tickets(
            mock_context, per_page=5, cursor="prev123", sort_order="asc"
        )

        # Verify pagination metadata is included
        assert result["has_more"] is True
        assert result["after_cursor"] == "abc123"

        # Verify API call parameters
        call_args = mock_httpx_client.get.call_args
        assert call_args[1]["params"]["page[size]"] == "5"
        assert call_args[1]["params"]["page[after]"] == "prev123"
        assert call_args[1]["params"]["sort"] == "id"  # asc order

    @pytest.mark.asyncio
    async def test_list_tickets_offset_pagination(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test listing tickets with offset pagination."""
        mock_context.get_secret.return_value = "test-subdomain"

        tickets_response = {
            "tickets": [{"id": 3, "subject": "Test", "status": "pending"}],
            "next_page": "https://test.zendesk.com/api/v2/tickets.json?page=3",
            "count": 50,
        }

        mock_httpx_client.get.return_value = mock_http_response(tickets_response)

        result = await list_tickets(
            mock_context, status="pending", page=2, per_page=10
        )

        # Verify offset pagination metadata
        assert "next_page" in result
        assert result["total_count"] == 50

        # Verify API call parameters
        call_args = mock_httpx_client.get.call_args
        assert call_args[1]["params"]["page"] == "2"
        assert call_args[1]["params"]["per_page"] == "10"
        assert call_args[1]["params"]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_tickets_no_tickets(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test when no tickets are found."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.return_value = mock_http_response({"tickets": []})

        result = await list_tickets(mock_context)

        assert result["tickets"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_list_tickets_error(self, mock_context, mock_httpx_client):
        """Test error handling for failed API call."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock error response that raise_for_status will catch
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        )
        mock_httpx_client.get.return_value = error_response

        with pytest.raises(ToolExecutionError):
            await list_tickets(mock_context)

    @pytest.mark.asyncio
    async def test_list_tickets_no_subdomain(self, mock_context):
        """Test when subdomain is not configured."""
        mock_context.get_secret.return_value = None

        with pytest.raises(ToolExecutionError):
            await list_tickets(mock_context)


class TestGetTicketComments:
    """Test get_ticket_comments functionality."""

    @pytest.mark.asyncio
    async def test_get_ticket_comments_success(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test successfully getting ticket comments."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock response data
        comments_response = {
            "comments": [
                {
                    "id": 1,
                    "body": "I cannot access my account. Please help!",
                    "author_id": 12345,
                    "created_at": "2024-01-15T10:00:00Z",
                    "public": True,
                    "attachments": [],
                },
                {
                    "id": 2,
                    "body": "I'll help you reset your password.",
                    "author_id": 67890,
                    "created_at": "2024-01-15T10:30:00Z",
                    "public": True,
                    "attachments": [
                        {
                            "file_name": "screenshot.png",
                            "content_url": "https://example.com/screenshot.png",
                            "size": 12345,
                        }
                    ],
                },
            ]
        }

        mock_httpx_client.get.return_value = mock_http_response(comments_response)

        result = await get_ticket_comments(mock_context, ticket_id=123)

        # Verify the result is structured data
        assert isinstance(result, dict)
        assert result["ticket_id"] == 123
        assert result["count"] == 2
        assert len(result["comments"]) == 2

        # Verify attachments are included
        assert result["comments"][1]["attachments"][0]["file_name"] == "screenshot.png"

        # Verify the API call
        mock_httpx_client.get.assert_called_once_with(
            "https://test-subdomain.zendesk.com/api/v2/tickets/123/comments.json",
            headers={
                "Authorization": "Bearer fake-token",
                "Content-Type": "application/json",
            },
        )

    @pytest.mark.asyncio
    async def test_get_ticket_comments_no_comments(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test when no comments are found."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.return_value = mock_http_response({"comments": []})

        result = await get_ticket_comments(mock_context, ticket_id=123)

        assert result["comments"] == []
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_ticket_comments_not_found(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test when ticket is not found."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.return_value = mock_http_response({}, status_code=404)

        with pytest.raises(ToolExecutionError):
            await get_ticket_comments(mock_context, ticket_id=999)

    @pytest.mark.asyncio
    async def test_get_ticket_comments_error(self, mock_context, mock_httpx_client):
        """Test error handling when API fails."""
        mock_context.get_secret.return_value = "test-subdomain"

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=MagicMock(status_code=500)
        )

        mock_httpx_client.get.return_value = error_response

        with pytest.raises(ToolExecutionError):
            await get_ticket_comments(mock_context, ticket_id=123)


class TestAddTicketComment:
    """Test add_ticket_comment functionality."""

    @pytest.mark.asyncio
    async def test_add_public_comment_success(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test successfully adding a public comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        ticket_response = {
            "ticket": {
                "id": 123,
                "subject": "Test ticket",
                "url": "https://test-subdomain.zendesk.com/api/v2/tickets/123.json",
            }
        }

        mock_httpx_client.put.return_value = mock_http_response(ticket_response)

        result = await add_ticket_comment(
            mock_context,
            ticket_id=123,
            comment_body="This is a test comment",
            public=True,
        )

        # Verify structured response
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["ticket_id"] == 123
        assert result["comment_type"] == "public"
        assert "ticket" in result

        # Verify ticket has html_url but not url
        assert "url" not in result["ticket"]
        assert "html_url" in result["ticket"]

        # Verify the API call
        mock_httpx_client.put.assert_called_once_with(
            "https://test-subdomain.zendesk.com/api/v2/tickets/123.json",
            headers={
                "Authorization": "Bearer fake-token",
                "Content-Type": "application/json",
            },
            json={"ticket": {"comment": {"body": "This is a test comment", "public": True}}},
        )

    @pytest.mark.asyncio
    async def test_add_comment_default_public(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test that comment defaults to public when not specified."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({"ticket": {"id": 123}})

        result = await add_ticket_comment(
            mock_context,
            ticket_id=123,
            comment_body="Test comment",
            # Not specifying public parameter
        )

        assert result["comment_type"] == "public"

        # Verify the API call has public=True
        call_args = mock_httpx_client.put.call_args
        assert call_args[1]["json"]["ticket"]["comment"]["public"] is True

    @pytest.mark.asyncio
    async def test_add_internal_comment_success(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test successfully adding an internal comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({"ticket": {"id": 456}})

        result = await add_ticket_comment(
            mock_context,
            ticket_id=456,
            comment_body="Internal note for agents",
            public=False,
        )

        assert result["comment_type"] == "internal"

    @pytest.mark.asyncio
    async def test_add_comment_error(self, mock_context, mock_httpx_client):
        """Test error handling when adding comment fails."""
        mock_context.get_secret.return_value = "test-subdomain"

        error_response = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=MagicMock(status_code=404)
        )
        mock_httpx_client.put.return_value = error_response

        with pytest.raises(ToolExecutionError):
            await add_ticket_comment(mock_context, ticket_id=999, comment_body="Test comment")


class TestMarkTicketSolved:
    """Test mark_ticket_solved functionality."""

    @pytest.mark.asyncio
    async def test_mark_solved_without_comment(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test marking ticket as solved without a comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        ticket_response = {
            "ticket": {
                "id": 789,
                "status": "solved",
                "url": "https://test-subdomain.zendesk.com/api/v2/tickets/789.json",
            }
        }

        mock_httpx_client.put.return_value = mock_http_response(ticket_response)

        result = await mark_ticket_solved(mock_context, ticket_id=789)

        # Verify structured response
        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["ticket_id"] == 789
        assert result["status"] == "solved"
        assert "comment_added" not in result

        # Verify ticket has html_url
        assert "html_url" in result["ticket"]
        assert "url" not in result["ticket"]

        # Verify the API call
        mock_httpx_client.put.assert_called_once_with(
            "https://test-subdomain.zendesk.com/api/v2/tickets/789.json",
            headers={
                "Authorization": "Bearer fake-token",
                "Content-Type": "application/json",
            },
            json={"ticket": {"status": "solved"}},
        )

    @pytest.mark.asyncio
    async def test_mark_solved_with_public_comment(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test marking ticket as solved with a public comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({"ticket": {"id": 123}})

        result = await mark_ticket_solved(
            mock_context,
            ticket_id=123,
            comment_body="Issue resolved by resetting password",
            comment_public=True,
        )

        assert result["comment_added"] is True
        assert result["comment_type"] == "public"

        # Verify the request body includes the comment
        call_args = mock_httpx_client.put.call_args
        request_body = call_args[1]["json"]
        assert request_body["ticket"]["status"] == "solved"
        assert request_body["ticket"]["comment"]["body"] == "Issue resolved by resetting password"
        assert request_body["ticket"]["comment"]["public"] is True

    @pytest.mark.asyncio
    async def test_mark_solved_with_comment_default_internal(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test marking ticket as solved with comment defaults to internal."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({"ticket": {"id": 555}})

        result = await mark_ticket_solved(
            mock_context,
            ticket_id=555,
            comment_body="Internal resolution note",
            # Not specifying comment_public, should default to False
        )

        assert result["comment_added"] is True
        assert result["comment_type"] == "internal"

        # Verify the comment is internal by default
        call_args = mock_httpx_client.put.call_args
        request_body = call_args[1]["json"]
        assert request_body["ticket"]["comment"]["public"] is False

    @pytest.mark.asyncio
    async def test_mark_solved_error(self, mock_context, mock_httpx_client):
        """Test error handling when marking ticket as solved fails."""
        mock_context.get_secret.return_value = "test-subdomain"

        error_response = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Forbidden", request=MagicMock(), response=MagicMock(status_code=403)
        )
        mock_httpx_client.put.return_value = error_response

        with pytest.raises(ToolExecutionError):
            await mark_ticket_solved(mock_context, ticket_id=999)


class TestAuthenticationAndSecrets:
    """Test authentication and secrets handling."""

    @pytest.mark.asyncio
    async def test_no_auth_token(self, mock_context, mock_httpx_client):
        """Test behavior when auth token is empty."""
        mock_context.get_auth_token_or_empty.return_value = ""
        mock_context.get_secret.return_value = "test-subdomain"

        # The tools should still attempt the API call with empty token
        error_response = MagicMock()
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=MagicMock(status_code=401)
        )
        mock_httpx_client.get.return_value = error_response

        with pytest.raises(ToolExecutionError):
            await list_tickets(mock_context)

        # Should be called with empty Bearer token
        call_args = mock_httpx_client.get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer "

    @pytest.mark.asyncio
    async def test_subdomain_from_secret(self, mock_context, mock_httpx_client, mock_http_response):
        """Test that subdomain is correctly retrieved from secrets."""
        mock_context.get_secret.return_value = "my-company"

        mock_httpx_client.get.return_value = mock_http_response({"tickets": []})

        await list_tickets(mock_context)

        # Verify the correct subdomain was used
        call_args = mock_httpx_client.get.call_args
        assert "https://my-company.zendesk.com" in call_args[0][0]