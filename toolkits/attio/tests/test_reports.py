"""Tests for Attio report operations."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arcade_attio.tools.reports import _col_letter, create_report


class TestColLetter:
    """Tests for the _col_letter helper function."""

    def test_single_letters(self):
        """Test single letter columns A-Z."""
        assert _col_letter(0) == "A"
        assert _col_letter(1) == "B"
        assert _col_letter(25) == "Z"

    def test_double_letters(self):
        """Test double letter columns AA-AZ, BA, etc."""
        assert _col_letter(26) == "AA"
        assert _col_letter(27) == "AB"
        assert _col_letter(51) == "AZ"
        assert _col_letter(52) == "BA"

    def test_triple_letters(self):
        """Test triple letter columns."""
        # 26 + 26*26 = 702 is AAA
        assert _col_letter(702) == "AAA"


class TestCreateReport:
    """Tests for create_report tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_report_basic(self, mock_context):
        """Test basic report generation."""
        mock_response = {
            "data": [
                {
                    "id": {"record_id": "abc-123"},
                    "values": {
                        "name": [{"value": "Acme Corp"}],
                        "status": [{"value": "Active"}],
                    },
                },
                {
                    "id": {"record_id": "def-456"},
                    "values": {
                        "name": [{"value": "Beta Inc"}],
                        "status": [{"value": "Prospect"}],
                    },
                },
            ]
        }

        with patch(
            "arcade_attio.tools.reports._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await create_report(mock_context, object_type="companies")

            assert result["total_records"] == 2
            assert result["object_type"] == "companies"
            assert "record_id" in result["headers"]
            assert "name" in result["headers"]
            assert "status" in result["headers"]
            assert len(result["rows"]) == 2

            # Verify sheets_data is valid JSON
            sheets_data = json.loads(result["sheets_data"])
            assert 1 in sheets_data or "1" in sheets_data  # Header row

    @pytest.mark.asyncio
    async def test_create_report_with_attributes(self, mock_context):
        """Test report with specific attributes."""
        mock_response = {
            "data": [
                {
                    "id": {"record_id": "abc-123"},
                    "values": {
                        "name": [{"value": "Acme Corp"}],
                        "status": [{"value": "Active"}],
                        "industry": [{"value": "Tech"}],
                    },
                },
            ]
        }

        with patch(
            "arcade_attio.tools.reports._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await create_report(
                mock_context,
                object_type="companies",
                attributes=["name", "status"],
            )

            # Should only include specified attributes plus record_id
            assert result["headers"] == ["record_id", "name", "status"]
            assert "industry" not in result["headers"]

    @pytest.mark.asyncio
    async def test_create_report_with_filter(self, mock_context):
        """Test report with filter applied."""
        mock_response = {"data": []}

        with patch(
            "arcade_attio.tools.reports._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await create_report(
                mock_context,
                object_type="companies",
                filter_json=['{"attribute": "status", "operator": "equals", "value": "Active"}'],
            )

            assert result["total_records"] == 0
            call_args = mock_request.call_args
            assert "filter" in call_args[0][2]

    @pytest.mark.asyncio
    async def test_create_report_sheets_data_format(self, mock_context):
        """Test that sheets_data is properly formatted for Google Sheets."""
        mock_response = {
            "data": [
                {
                    "id": {"record_id": "abc-123"},
                    "values": {"name": [{"value": "Acme"}]},
                },
            ]
        }

        with patch(
            "arcade_attio.tools.reports._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await create_report(
                mock_context,
                object_type="companies",
                attributes=["name"],
            )

            sheets_data = json.loads(result["sheets_data"])

            # Row 1 should be headers
            assert sheets_data["1"]["A"] == "record_id"
            assert sheets_data["1"]["B"] == "name"

            # Row 2 should be data
            assert sheets_data["2"]["A"] == "abc-123"
            assert sheets_data["2"]["B"] == "Acme"
