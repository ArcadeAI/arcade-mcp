import pytest
from unittest.mock import MagicMock
from arcade_zendesk.tools.tickets import (
    list_tickets,
    get_ticket_comments,
    add_ticket_comment,
    mark_ticket_solved,
)


class TestListTickets:
    """Test list_tickets functionality."""

    @pytest.mark.asyncio
    async def test_list_tickets_success(self, mock_context, mock_httpx_client, mock_http_response):
        """Test successful listing of open tickets."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock response data
        tickets_response = {
            "tickets": [
                {"id": 1, "subject": "Login issue", "status": "open"},
                {"id": 2, "subject": "Password reset request", "status": "open"},
            ]
        }

        mock_httpx_client.get.return_value = mock_http_response(tickets_response)

        result = await list_tickets(mock_context)

        # Verify the result
        expected_result = (
            "Ticket #1: Login issue (Status: open)\n"
            "Ticket #2: Password reset request (Status: open)"
        )
        assert result == expected_result

        # Verify the API call
        mock_httpx_client.get.assert_called_once_with(
            "https://test-subdomain.zendesk.com/api/v2/tickets.json?status=open",
            headers={
                "Authorization": "Bearer fake-token",
                "Content-Type": "application/json",
            },
        )

    @pytest.mark.asyncio
    async def test_list_tickets_no_tickets(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test when no open tickets are found."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.return_value = mock_http_response({"tickets": []})

        result = await list_tickets(mock_context)

        assert result == "No open tickets found."

    @pytest.mark.asyncio
    async def test_list_tickets_error(self, mock_context, mock_httpx_client):
        """Test error handling for failed API call."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock error response
        error_response = MagicMock()
        error_response.status_code = 401
        error_response.text = "Unauthorized"
        mock_httpx_client.get.return_value = error_response

        result = await list_tickets(mock_context)

        assert result == "Error fetching tickets: 401 - Unauthorized"

    @pytest.mark.asyncio
    async def test_list_tickets_no_subdomain(self, mock_context):
        """Test when subdomain is not configured."""
        mock_context.get_secret.return_value = None

        # Should raise an error when trying to format the URL
        with pytest.raises(Exception):
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
                },
                {
                    "id": 2,
                    "body": "I'll help you reset your password.",
                    "author_id": 67890,
                    "created_at": "2024-01-15T10:30:00Z",
                    "public": True,
                },
                {
                    "id": 3,
                    "body": "Internal note: User verified via security questions",
                    "author_id": 67890,
                    "created_at": "2024-01-15T10:35:00Z",
                    "public": False,
                },
            ]
        }

        mock_httpx_client.get.return_value = mock_http_response(comments_response)

        result = await get_ticket_comments(mock_context, ticket_id=123)

        # Verify the result
        assert "Comments for Ticket #123:" in result
        assert "=== Original Description ===" in result
        assert "I cannot access my account. Please help!" in result
        assert "=== Comment #1 (Public) ===" in result
        assert "=== Comment #2 (Internal) ===" in result
        assert "Author ID: 12345" in result
        assert "Created: 2024-01-15T10:00:00Z" in result

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

        assert result == "No comments found for ticket #123."

    @pytest.mark.asyncio
    async def test_get_ticket_comments_not_found(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test when ticket is not found."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.get.return_value = mock_http_response({}, status_code=404)

        result = await get_ticket_comments(mock_context, ticket_id=999)

        assert result == "Ticket #999 not found."

    @pytest.mark.asyncio
    async def test_get_ticket_comments_error(self, mock_context, mock_httpx_client):
        """Test error handling when API fails."""
        mock_context.get_secret.return_value = "test-subdomain"

        error_response = MagicMock()
        error_response.status_code = 500
        error_response.text = "Internal Server Error"

        mock_httpx_client.get.return_value = error_response

        result = await get_ticket_comments(mock_context, ticket_id=123)

        assert result == "Error fetching comments: 500 - Internal Server Error"


class TestAddTicketComment:
    """Test add_ticket_comment functionality."""

    @pytest.mark.asyncio
    async def test_add_public_comment_success(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test successfully adding a public comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({}, status_code=200)

        result = await add_ticket_comment(
            mock_context,
            ticket_id=123,
            comment_body="This is a test comment",
            public=True,
        )

        assert result == "Successfully added public comment to ticket #123"

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
    async def test_add_internal_comment_success(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test successfully adding an internal comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({}, status_code=200)

        result = await add_ticket_comment(
            mock_context,
            ticket_id=456,
            comment_body="Internal note for agents",
            public=False,
        )

        assert result == "Successfully added internal comment to ticket #456"

    @pytest.mark.asyncio
    async def test_add_comment_error(self, mock_context, mock_httpx_client):
        """Test error handling when adding comment fails."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock error response
        error_response = MagicMock()
        error_response.status_code = 404
        error_response.text = "Ticket not found"
        error_response.headers.get.return_value = "text/plain"
        mock_httpx_client.put.return_value = error_response

        result = await add_ticket_comment(mock_context, ticket_id=999, comment_body="Test comment")

        assert result == "Error adding comment to ticket: 404 - Ticket not found"

    @pytest.mark.asyncio
    async def test_add_comment_json_error(self, mock_context, mock_httpx_client):
        """Test error handling with JSON error response."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock JSON error response
        error_response = MagicMock()
        error_response.status_code = 422
        error_response.headers.get.return_value = "application/json"
        error_response.json.return_value = {"error": "Invalid request format"}
        mock_httpx_client.put.return_value = error_response

        result = await add_ticket_comment(mock_context, ticket_id=123, comment_body="Test")

        assert result == "Error adding comment to ticket: 422 - Invalid request format"


class TestMarkTicketSolved:
    """Test mark_ticket_solved functionality."""

    @pytest.mark.asyncio
    async def test_mark_solved_without_comment(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test marking ticket as solved without a comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({}, status_code=200)

        result = await mark_ticket_solved(mock_context, ticket_id=789)

        assert result == "Successfully marked ticket #789 as solved"

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

        mock_httpx_client.put.return_value = mock_http_response({}, status_code=200)

        result = await mark_ticket_solved(
            mock_context,
            ticket_id=123,
            comment_body="Issue resolved by resetting password",
            comment_public=True,
        )

        assert result == "Successfully marked ticket #123 as solved with public resolution comment"

        # Verify the request body includes the comment
        call_args = mock_httpx_client.put.call_args
        request_body = call_args[1]["json"]
        assert request_body["ticket"]["status"] == "solved"
        assert request_body["ticket"]["comment"]["body"] == "Issue resolved by resetting password"
        assert request_body["ticket"]["comment"]["public"] is True

    @pytest.mark.asyncio
    async def test_mark_solved_with_internal_comment(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test marking ticket as solved with an internal comment."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({}, status_code=200)

        result = await mark_ticket_solved(
            mock_context,
            ticket_id=456,
            comment_body="Resolved via backend fix",
            comment_public=False,
        )

        assert (
            result == "Successfully marked ticket #456 as solved with internal resolution comment"
        )

    @pytest.mark.asyncio
    async def test_mark_solved_with_comment_default_internal(
        self, mock_context, mock_httpx_client, mock_http_response
    ):
        """Test marking ticket as solved with comment defaults to internal."""
        mock_context.get_secret.return_value = "test-subdomain"

        mock_httpx_client.put.return_value = mock_http_response({}, status_code=200)

        result = await mark_ticket_solved(
            mock_context,
            ticket_id=555,
            comment_body="Internal resolution note",
            # Not specifying comment_public, should default to False
        )

        assert (
            result == "Successfully marked ticket #555 as solved with internal resolution comment"
        )

        # Verify the comment is internal by default
        call_args = mock_httpx_client.put.call_args
        request_body = call_args[1]["json"]
        assert request_body["ticket"]["comment"]["public"] is False

    @pytest.mark.asyncio
    async def test_mark_solved_error(self, mock_context, mock_httpx_client):
        """Test error handling when marking ticket as solved fails."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock error response
        error_response = MagicMock()
        error_response.status_code = 403
        error_response.text = "Permission denied"
        error_response.headers.get.return_value = "text/plain"
        mock_httpx_client.put.return_value = error_response

        result = await mark_ticket_solved(mock_context, ticket_id=999)

        assert result == "Error marking ticket as solved: 403 - Permission denied"

    @pytest.mark.asyncio
    async def test_mark_solved_json_error(self, mock_context, mock_httpx_client):
        """Test error handling with JSON error response."""
        mock_context.get_secret.return_value = "test-subdomain"

        # Mock JSON error response
        error_response = MagicMock()
        error_response.status_code = 422
        error_response.headers.get.return_value = "application/json"
        error_response.json.return_value = {"error": "Ticket already closed"}
        mock_httpx_client.put.return_value = error_response

        result = await mark_ticket_solved(mock_context, ticket_id=123)

        assert result == "Error marking ticket as solved: 422 - Ticket already closed"


class TestAuthenticationAndSecrets:
    """Test authentication and secrets handling."""

    @pytest.mark.asyncio
    async def test_no_auth_token(self, mock_context, mock_httpx_client):
        """Test behavior when auth token is empty."""
        mock_context.get_auth_token_or_empty.return_value = ""
        mock_context.get_secret.return_value = "test-subdomain"

        # The tools should still attempt the API call with empty token
        mock_httpx_client.get.return_value = MagicMock(status_code=401, text="Unauthorized")

        result = await list_tickets(mock_context)

        # Should be called with empty Bearer token
        call_args = mock_httpx_client.get.call_args
        assert call_args[1]["headers"]["Authorization"] == "Bearer "
        assert "Error fetching tickets: 401" in result

    @pytest.mark.asyncio
    async def test_subdomain_from_secret(self, mock_context, mock_httpx_client, mock_http_response):
        """Test that subdomain is correctly retrieved from secrets."""
        mock_context.get_secret.return_value = "my-company"

        mock_httpx_client.get.return_value = mock_http_response({"tickets": []})

        await list_tickets(mock_context)

        # Verify the correct subdomain was used
        call_args = mock_httpx_client.get.call_args
        assert "https://my-company.zendesk.com" in call_args[0][0]
