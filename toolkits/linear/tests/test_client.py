import pytest
from unittest.mock import AsyncMock, patch
import httpx
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.client import LinearClient


class TestLinearClient:
    """Tests for LinearClient"""

    @pytest.mark.asyncio
    async def test_client_init(self):
        """Test client initialization"""
        client = LinearClient("test_token")
        assert client.auth_token == "test_token"
        assert client.api_url == "https://api.linear.app/graphql"
        assert client.max_concurrent_requests == 3
        assert client.timeout_seconds == 30

    def test_build_headers(self):
        """Test header building"""
        client = LinearClient("test_token")
        headers = client._build_headers()
        
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"

    def test_build_headers_with_additional(self):
        """Test header building with additional headers"""
        client = LinearClient("test_token")
        additional = {"X-Custom": "value"}
        headers = client._build_headers(additional)
        
        assert headers["Authorization"] == "Bearer test_token"
        assert headers["X-Custom"] == "value"

    def test_build_error_message_graphql_single(self):
        """Test error message building for single GraphQL error"""
        client = LinearClient("test_token")
        
        # Mock response with single GraphQL error
        response = AsyncMock()
        response.status_code = 200
        response.json = lambda: {
            "errors": [
                {
                    "message": "Field not found",
                    "extensions": {"code": "FIELD_ERROR"}
                }
            ]
        }
        
        user_msg, dev_msg = client._build_error_message(response)
        
        assert user_msg == "Field not found"
        assert "Field not found" in dev_msg
        assert "FIELD_ERROR" in dev_msg

    def test_build_error_message_graphql_multiple(self):
        """Test error message building for multiple GraphQL errors"""
        client = LinearClient("test_token")
        
        # Mock response with multiple GraphQL errors
        response = AsyncMock()
        response.status_code = 200
        response.json = lambda: {
            "errors": [
                {"message": "Error 1"},
                {"message": "Error 2"}
            ]
        }
        
        user_msg, dev_msg = client._build_error_message(response)
        
        assert user_msg == "Multiple errors: Error 1; Error 2"
        assert "Multiple GraphQL errors" in dev_msg

    def test_build_error_message_http_error(self):
        """Test error message building for HTTP errors"""
        client = LinearClient("test_token")
        
        # Mock HTTP error response with valid JSON but no GraphQL errors
        response = AsyncMock()
        response.status_code = 401
        response.reason_phrase = "Unauthorized"
        response.text = "Authentication required"
        
        # Return valid JSON that doesn't have "errors" field
        response.json = lambda: {"message": "Authentication required"}
        
        user_msg, dev_msg = client._build_error_message(response)
        
        assert user_msg == "HTTP 401: Unauthorized"
        assert "HTTP 401: Authentication required" in dev_msg

    @pytest.mark.asyncio
    async def test_raise_for_status_success(self):
        """Test _raise_for_status with successful response"""
        client = LinearClient("test_token")
        
        # Mock successful response
        response = AsyncMock()
        response.status_code = 200
        response.json = lambda: {"data": {"viewer": {"id": "user_1"}}}
        
        # Should not raise exception
        client._raise_for_status(response)

    @pytest.mark.asyncio
    async def test_raise_for_status_graphql_error(self):
        """Test _raise_for_status with GraphQL errors"""
        client = LinearClient("test_token")
        
        # Mock response with GraphQL errors
        response = AsyncMock()
        response.status_code = 200
        response.json = lambda: {
            "errors": [{"message": "Invalid field"}]
        }
        
        with pytest.raises(ToolExecutionError) as exc_info:
            client._raise_for_status(response)
        
        assert "Invalid field" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_raise_for_status_http_error(self):
        """Test _raise_for_status with HTTP errors"""
        client = LinearClient("test_token")
        
        # Mock HTTP error response with valid JSON but no GraphQL errors
        response = AsyncMock()
        response.status_code = 401
        response.reason_phrase = "Unauthorized"
        response.text = "Authentication required"
        
        # Return valid JSON that doesn't have "errors" field
        response.json = lambda: {"message": "Authentication required"}
        
        with pytest.raises(ToolExecutionError) as exc_info:
            client._raise_for_status(response)
        
        assert "HTTP 401: Unauthorized" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_execute_query_success(self, mock_http_client):
        """Test successful GraphQL query execution"""
        client = LinearClient("test_token")
        
        # Mock HTTP client and response
        mock_client_instance = AsyncMock()
        mock_http_client.return_value.__aenter__.return_value = mock_client_instance
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "data": {"viewer": {"id": "user_1"}}
        }
        mock_client_instance.post.return_value = mock_response
        
        query = "query { viewer { id } }"
        variables = {"test": "value"}
        
        result = await client.execute_query(query, variables)
        
        assert result["data"]["viewer"]["id"] == "user_1"
        mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_execute_query_with_operation_name(self, mock_http_client):
        """Test GraphQL query execution with operation name"""
        client = LinearClient("test_token")
        
        # Mock HTTP client and response
        mock_client_instance = AsyncMock()
        mock_http_client.return_value.__aenter__.return_value = mock_client_instance
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {"data": {}}
        mock_client_instance.post.return_value = mock_response
        
        query = "query GetViewer { viewer { id } }"
        
        await client.execute_query(query, operation_name="GetViewer")
        
        # Verify payload includes operation name
        call_args = mock_client_instance.post.call_args
        payload = call_args[1]["json"]
        assert payload["operationName"] == "GetViewer"

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_execute_mutation(self, mock_http_client):
        """Test GraphQL mutation execution"""
        client = LinearClient("test_token")
        
        # Mock HTTP client and response
        mock_client_instance = AsyncMock()
        mock_http_client.return_value.__aenter__.return_value = mock_client_instance
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = lambda: {
            "data": {"issueCreate": {"success": True}}
        }
        mock_client_instance.post.return_value = mock_response
        
        mutation = "mutation { issueCreate(input: {}) { success } }"
        
        result = await client.execute_mutation(mutation)
        
        assert result["data"]["issueCreate"]["success"] is True

    @pytest.mark.asyncio
    @patch("arcade_linear.client.LinearClient.execute_query")
    async def test_get_viewer(self, mock_execute_query):
        """Test get_viewer method"""
        client = LinearClient("test_token")
        
        mock_execute_query.return_value = {
            "data": {
                "viewer": {
                    "id": "user_1",
                    "name": "John Doe",
                    "email": "john@company.com"
                }
            }
        }
        
        result = await client.get_viewer()
        
        assert result["id"] == "user_1"
        assert result["name"] == "John Doe"
        assert result["email"] == "john@company.com"
        mock_execute_query.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.client.LinearClient.execute_query")
    async def test_get_teams(self, mock_execute_query):
        """Test get_teams method"""
        client = LinearClient("test_token")
        
        mock_execute_query.return_value = {
            "data": {
                "teams": {
                    "nodes": [
                        {
                            "id": "team_1",
                            "name": "Frontend",
                            "key": "FE"
                        }
                    ],
                    "pageInfo": {"hasNextPage": False}
                }
            }
        }
        
        result = await client.get_teams(first=10, include_archived=True)
        
        assert len(result["nodes"]) == 1
        assert result["nodes"][0]["name"] == "Frontend"
        assert result["pageInfo"]["hasNextPage"] is False
        mock_execute_query.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.client.LinearClient.execute_query")
    async def test_get_issue_by_id(self, mock_execute_query):
        """Test get_issue_by_id method"""
        client = LinearClient("test_token")
        
        mock_execute_query.return_value = {
            "data": {
                "issue": {
                    "id": "issue_1",
                    "identifier": "FE-123",
                    "title": "Test issue"
                }
            }
        }
        
        result = await client.get_issue_by_id("FE-123")
        
        assert result["id"] == "issue_1"
        assert result["identifier"] == "FE-123"
        assert result["title"] == "Test issue"
        mock_execute_query.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.client.LinearClient.execute_mutation")
    async def test_create_issue(self, mock_execute_mutation):
        """Test create_issue method"""
        client = LinearClient("test_token")
        
        mock_execute_mutation.return_value = {
            "data": {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue_1",
                        "identifier": "FE-124",
                        "title": "New issue"
                    }
                }
            }
        }
        
        input_data = {"title": "New issue", "teamId": "team_1"}
        result = await client.create_issue(input_data)
        
        assert result["success"] is True
        assert result["issue"]["identifier"] == "FE-124"
        mock_execute_mutation.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.client.LinearClient.execute_mutation")
    async def test_update_issue(self, mock_execute_mutation):
        """Test update_issue method"""
        client = LinearClient("test_token")
        
        mock_execute_mutation.return_value = {
            "data": {
                "issueUpdate": {
                    "success": True,
                    "issue": {
                        "id": "issue_1",
                        "identifier": "FE-123",
                        "title": "Updated title"
                    }
                }
            }
        }
        
        input_data = {"title": "Updated title"}
        result = await client.update_issue("FE-123", input_data)
        
        assert result["success"] is True
        assert result["issue"]["title"] == "Updated title"
        mock_execute_mutation.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.client.LinearClient.execute_query")
    async def test_get_user_by_email(self, mock_execute_query):
        """Test get_user_by_email method"""
        client = LinearClient("test_token")
        
        mock_execute_query.return_value = {
            "data": {
                "users": {
                    "nodes": [
                        {
                            "id": "user_1",
                            "name": "John Doe",
                            "email": "john@company.com"
                        }
                    ]
                }
            }
        }
        
        result = await client.get_user_by_email("john@company.com")
        
        assert result["id"] == "user_1"
        assert result["email"] == "john@company.com"
        mock_execute_query.assert_called_once()

    @pytest.mark.asyncio
    @patch("arcade_linear.client.LinearClient.execute_query")
    async def test_get_user_by_email_not_found(self, mock_execute_query):
        """Test get_user_by_email when user not found"""
        client = LinearClient("test_token")
        
        mock_execute_query.return_value = {
            "data": {
                "users": {
                    "nodes": []
                }
            }
        }
        
        result = await client.get_user_by_email("nonexistent@company.com")
        
        assert result is None
        mock_execute_query.assert_called_once() 