"""Tests for Attio list operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arcade_attio.tools.lists import (
    add_to_list,
    get_list_entries,
    list_lists,
    remove_from_list,
)


class TestListLists:
    """Tests for list_lists tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_list_lists(self, mock_context):
        """Test getting all lists."""
        mock_response = {
            "data": [
                {
                    "id": {"list_id": "list-1"},
                    "name": "Active Prospects",
                    "parent_object": "companies",
                },
                {
                    "id": {"list_id": "list-2"},
                    "name": "Outbound Targets",
                    "parent_object": "people",
                },
            ]
        }

        with patch(
            "arcade_attio.tools.lists._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await list_lists(mock_context)

            assert len(result["lists"]) == 2
            assert result["lists"][0]["name"] == "Active Prospects"
            assert result["lists"][1]["parent_object"] == "people"


class TestGetListEntries:
    """Tests for get_list_entries tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_list_entries(self, mock_context):
        """Test getting list entries."""
        mock_response = {
            "data": [
                {
                    "id": {"entry_id": "entry-1"},
                    "record_id": "record-abc",
                    "values": {"stage": [{"value": "Engaged"}]},
                },
                {
                    "id": {"entry_id": "entry-2"},
                    "record_id": "record-def",
                    "values": {"stage": [{"value": "Contacted"}]},
                },
            ]
        }

        with patch(
            "arcade_attio.tools.lists._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await get_list_entries(mock_context, list_id="list-123")

            assert result["total"] == 2
            assert result["entries"][0]["entry_id"] == "entry-1"
            assert result["entries"][0]["record_id"] == "record-abc"
            assert result["entries"][0]["stage"] == "Engaged"


class TestAddToList:
    """Tests for add_to_list tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_add_to_list(self, mock_context):
        """Test adding a record to a list."""
        mock_response = {
            "data": {
                "id": {"entry_id": "new-entry-123"},
            }
        }

        with patch(
            "arcade_attio.tools.lists._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await add_to_list(mock_context, list_id="list-123", record_id="record-abc")

            assert result["entry_id"] == "new-entry-123"
            assert result["status"] == "added"

    @pytest.mark.asyncio
    async def test_add_to_list_with_values(self, mock_context):
        """Test adding a record with entry-specific values."""
        mock_response = {
            "data": {
                "id": {"entry_id": "new-entry-456"},
            }
        }

        with patch(
            "arcade_attio.tools.lists._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await add_to_list(
                mock_context,
                list_id="list-123",
                record_id="record-abc",
                entry_values={"stage": "Qualified"},
            )

            assert result["entry_id"] == "new-entry-456"
            call_args = mock_request.call_args
            assert "values" in call_args[0][2]["data"]


class TestRemoveFromList:
    """Tests for remove_from_list tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_remove_from_list(self, mock_context):
        """Test removing an entry from a list."""
        with patch(
            "arcade_attio.tools.lists._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {}

            result = await remove_from_list(mock_context, list_id="list-123", entry_id="entry-abc")

            assert result["status"] == "removed"
            mock_request.assert_called_once_with("DELETE", "/lists/list-123/entries/entry-abc")
