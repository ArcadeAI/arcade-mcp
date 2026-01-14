"""Tests for Attio workspace operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arcade_attio.tools.workspace import list_workspace_members


class TestListWorkspaceMembers:
    """Tests for list_workspace_members tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_list_workspace_members(self, mock_context):
        """Test getting all workspace members."""
        mock_response = {
            "data": [
                {
                    "id": {"workspace_member_id": "member-1"},
                    "first_name": "John",
                    "last_name": "Doe",
                    "email_address": "john@example.com",
                },
                {
                    "id": {"workspace_member_id": "member-2"},
                    "first_name": "Jane",
                    "last_name": "Smith",
                    "email_address": "jane@example.com",
                },
            ]
        }

        with patch(
            "arcade_attio.tools.workspace._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await list_workspace_members(mock_context)

            assert len(result["members"]) == 2
            assert result["members"][0]["member_id"] == "member-1"
            assert result["members"][0]["name"] == "John Doe"
            assert result["members"][0]["email"] == "john@example.com"
            assert result["members"][1]["name"] == "Jane Smith"

    @pytest.mark.asyncio
    async def test_list_workspace_members_empty(self, mock_context):
        """Test when workspace has no members."""
        mock_response = {"data": []}

        with patch(
            "arcade_attio.tools.workspace._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await list_workspace_members(mock_context)

            assert len(result["members"]) == 0

    @pytest.mark.asyncio
    async def test_list_workspace_members_missing_fields(self, mock_context):
        """Test handling members with missing name fields."""
        mock_response = {
            "data": [
                {
                    "id": {"workspace_member_id": "member-1"},
                    "first_name": "John",
                    "email_address": "john@example.com",
                },
                {
                    "id": {"workspace_member_id": "member-2"},
                    "last_name": "Smith",
                    "email_address": "smith@example.com",
                },
            ]
        }

        with patch(
            "arcade_attio.tools.workspace._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await list_workspace_members(mock_context)

            assert result["members"][0]["name"] == "John"
            assert result["members"][1]["name"] == "Smith"
