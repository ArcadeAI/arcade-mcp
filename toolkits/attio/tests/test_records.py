"""Tests for Attio record operations."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arcade_attio.tools.records import (
    _flatten_record,
    assert_record,
    get_record,
    query_records,
    search_records,
)


class TestFlattenRecord:
    """Tests for the _flatten_record helper function."""

    def test_flatten_record_basic(self):
        """Test basic record flattening."""
        record = {
            "id": {"record_id": "abc-123"},
            "values": {
                "name": [{"value": "Acme Corp"}],
                "status": [{"value": "Active"}],
            },
        }
        result = _flatten_record(record)
        assert result["record_id"] == "abc-123"
        assert result["name"] == "Acme Corp"
        assert result["status"] == "Active"

    def test_flatten_record_empty_values(self):
        """Test flattening record with empty values."""
        record = {
            "id": {"record_id": "abc-123"},
            "values": {
                "name": [],
                "email": None,
            },
        }
        result = _flatten_record(record)
        assert result["record_id"] == "abc-123"
        assert "name" not in result
        assert "email" not in result

    def test_flatten_record_email_address(self):
        """Test flattening record with email_address field."""
        record = {
            "id": {"record_id": "person-123"},
            "values": {
                "email_addresses": [{"email_address": "test@example.com"}],
            },
        }
        result = _flatten_record(record)
        assert result["email_addresses"] == "test@example.com"

    def test_flatten_record_domain(self):
        """Test flattening record with domain field."""
        record = {
            "id": {"record_id": "company-123"},
            "values": {
                "domains": [{"domain": "example.com"}],
            },
        }
        result = _flatten_record(record)
        assert result["domains"] == "example.com"


class TestQueryRecords:
    """Tests for query_records tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        context = MagicMock()
        return context

    @pytest.mark.asyncio
    async def test_query_records_basic(self, mock_context):
        """Test basic query without filters."""
        mock_response = {
            "data": [
                {
                    "id": {"record_id": "abc-123"},
                    "values": {"name": [{"value": "Acme Corp"}]},
                },
                {
                    "id": {"record_id": "def-456"},
                    "values": {"name": [{"value": "Beta Inc"}]},
                },
            ]
        }

        with patch(
            "arcade_attio.tools.records._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await query_records(mock_context, object_type="companies", limit=100)

            assert result["total"] == 2
            assert len(result["records"]) == 2
            assert result["records"][0]["name"] == "Acme Corp"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_records_with_filter(self, mock_context):
        """Test query with filter."""
        mock_response = {"data": []}

        with patch(
            "arcade_attio.tools.records._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await query_records(
                mock_context,
                object_type="companies",
                filter_json=['{"attribute": "status", "operator": "equals", "value": "Active"}'],
            )

            assert result["total"] == 0
            call_args = mock_request.call_args
            assert "filter" in call_args[0][2]  # json_data


class TestGetRecord:
    """Tests for get_record tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_record(self, mock_context):
        """Test getting a single record."""
        mock_response = {
            "data": {
                "id": {"record_id": "abc-123"},
                "values": {"name": [{"value": "Acme Corp"}], "domain": [{"value": "acme.com"}]},
            }
        }

        with patch(
            "arcade_attio.tools.records._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await get_record(mock_context, object_type="companies", record_id="abc-123")

            assert result["record_id"] == "abc-123"
            assert "web_url" in result
            assert "acme.com" in str(result["values"])


class TestAssertRecord:
    """Tests for assert_record (upsert) tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_assert_record(self, mock_context):
        """Test upserting a record."""
        mock_response = {
            "data": {
                "id": {"record_id": "new-123"},
            }
        }

        with (
            patch("arcade_attio.tools.records._get_api_key", return_value="test-key"),
            patch("httpx.AsyncClient") as mock_client_class,
        ):
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response_obj = MagicMock()
            mock_response_obj.json.return_value = mock_response
            mock_client.put.return_value = mock_response_obj

            result = await assert_record(
                mock_context,
                object_type="companies",
                matching_attribute="domains",
                values={"domains": [{"domain": "newcompany.com"}], "name": "New Company"},
            )

            assert result["record_id"] == "new-123"
            assert result["matched_on"] == "domains"


class TestSearchRecords:
    """Tests for search_records tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_search_records(self, mock_context):
        """Test searching records by name."""
        mock_response = {
            "data": [
                {
                    "id": {"record_id": "abc-123"},
                    "values": {"name": [{"value": "Acme Corp"}]},
                },
                {
                    "id": {"record_id": "def-456"},
                    "values": {"name": [{"value": "Beta Inc"}]},
                },
            ]
        }

        with patch(
            "arcade_attio.tools.records._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await search_records(mock_context, query="acme", object_type="companies")

            assert result["total"] == 1
            assert result["results"][0]["name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_search_records_no_match(self, mock_context):
        """Test search with no matching results."""
        mock_response = {
            "data": [
                {
                    "id": {"record_id": "abc-123"},
                    "values": {"name": [{"value": "Acme Corp"}]},
                },
            ]
        }

        with patch(
            "arcade_attio.tools.records._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await search_records(mock_context, query="xyz", object_type="companies")

            assert result["total"] == 0
