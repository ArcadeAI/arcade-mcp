from unittest.mock import Mock, patch

import httpx
import pytest

from arcade_zendesk.who_am_i_util import (
    WhoAmIResponse,
    _extract_organization_info,
    _extract_user_info,
    _get_current_user,
    _get_organization_info,
    build_who_am_i_response,
)


@pytest.fixture
def mock_context():
    """Create a mock ToolContext for testing."""
    context = Mock()
    context.get_secret.return_value = "test-subdomain"
    context.get_auth_token_or_empty.return_value = "test-token"
    return context


@pytest.fixture
def sample_user_data():
    """Sample user data from Zendesk API."""
    return {
        "id": 12345,
        "name": "John Doe",
        "email": "john.doe@example.com",
        "role": "admin",
        "active": True,
        "verified": True,
        "locale": "en-US",
        "time_zone": "America/New_York",
        "organization_id": 67890,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2023-12-01T00:00:00Z",
    }


@pytest.fixture
def sample_organization_data():
    """Sample organization data from Zendesk API."""
    return {
        "id": 67890,
        "name": "Example Corp",
        "domain_names": ["example.com", "example.org"],
        "created_at": "2022-01-01T00:00:00Z",
        "updated_at": "2023-11-01T00:00:00Z",
        "details": "Main organization",
        "notes": "Primary customer",
        "group_id": 123,
        "shared_tickets": True,
        "shared_comments": False,
    }


class TestBuildWhoAmIResponse:
    """Test the main build_who_am_i_response function."""

    @pytest.mark.asyncio
    async def test_build_complete_response(
        self, mock_context, sample_user_data, sample_organization_data
    ):
        """Test building a complete who am I response."""
        with (
            patch("arcade_zendesk.who_am_i_util._get_current_user") as mock_get_user,
            patch("arcade_zendesk.who_am_i_util._get_organization_info") as mock_get_org,
        ):
            mock_get_user.return_value = sample_user_data
            mock_get_org.return_value = sample_organization_data

            result = await build_who_am_i_response(mock_context)

            assert isinstance(result, dict)
            assert result["user_id"] == 12345
            assert result["name"] == "John Doe"
            assert result["email"] == "john.doe@example.com"
            assert result["role"] == "admin"
            assert result["active"] is True
            assert result["verified"] is True
            assert result["locale"] == "en-US"
            assert result["time_zone"] == "America/New_York"
            assert result["organization_id"] == 67890
            assert result["organization_name"] == "Example Corp"
            assert result["organization_domains"] == ["example.com", "example.org"]
            assert result["zendesk_access"] is True

            mock_get_user.assert_called_once_with(mock_context)
            mock_get_org.assert_called_once_with(mock_context, 67890)

    @pytest.mark.asyncio
    async def test_build_response_without_organization(self, mock_context, sample_user_data):
        """Test building response when user has no organization."""
        user_data_no_org = sample_user_data.copy()
        del user_data_no_org["organization_id"]

        with (
            patch("arcade_zendesk.who_am_i_util._get_current_user") as mock_get_user,
            patch("arcade_zendesk.who_am_i_util._get_organization_info") as mock_get_org,
        ):
            mock_get_user.return_value = user_data_no_org
            mock_get_org.return_value = {}

            result = await build_who_am_i_response(mock_context)

            assert result["user_id"] == 12345
            assert result["name"] == "John Doe"
            assert result["zendesk_access"] is True
            assert "organization_name" not in result
            assert "organization_domains" not in result

            mock_get_org.assert_called_once_with(mock_context, None)


class TestGetCurrentUser:
    """Test the _get_current_user function."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, mock_context, sample_user_data):
        """Test successful user retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {"user": sample_user_data}
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await _get_current_user(mock_context)

            assert result == sample_user_data
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                "https://test-subdomain.zendesk.com/api/v2/users/me",
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
            )

    @pytest.mark.asyncio
    async def test_get_current_user_http_error(self, mock_context):
        """Test user retrieval with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock())
            )

            with pytest.raises(httpx.HTTPStatusError):
                await _get_current_user(mock_context)


class TestGetOrganizationInfo:
    """Test the _get_organization_info function."""

    @pytest.mark.asyncio
    async def test_get_organization_info_success(self, mock_context, sample_organization_data):
        """Test successful organization retrieval."""
        mock_response = Mock()
        mock_response.json.return_value = {"organization": sample_organization_data}
        mock_response.raise_for_status.return_value = None

        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await _get_organization_info(mock_context, 67890)

            assert result == sample_organization_data
            mock_client.return_value.__aenter__.return_value.get.assert_called_once_with(
                "https://test-subdomain.zendesk.com/api/v2/organizations/67890",
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
            )

    @pytest.mark.asyncio
    async def test_get_organization_info_no_id(self, mock_context):
        """Test organization retrieval with no organization ID."""
        result = await _get_organization_info(mock_context, None)
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_organization_info_http_error(self, mock_context):
        """Test organization retrieval with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.HTTPStatusError("404 Not Found", request=Mock(), response=Mock())
            )

            with pytest.raises(httpx.HTTPStatusError):
                await _get_organization_info(mock_context, 67890)


class TestExtractUserInfo:
    """Test the _extract_user_info function."""

    def test_extract_complete_user_info(self, sample_user_data):
        """Test extracting complete user information."""
        result = _extract_user_info(sample_user_data)

        expected = {
            "user_id": 12345,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "role": "admin",
            "active": True,
            "verified": True,
            "locale": "en-US",
            "time_zone": "America/New_York",
            "organization_id": 67890,
        }

        assert result == expected

    def test_extract_partial_user_info(self):
        """Test extracting partial user information."""
        partial_data = {
            "id": 12345,
            "name": "John Doe",
            "email": "john.doe@example.com",
        }

        result = _extract_user_info(partial_data)

        expected = {
            "user_id": 12345,
            "name": "John Doe",
            "email": "john.doe@example.com",
        }

        assert result == expected

    def test_extract_empty_user_info(self):
        """Test extracting from empty user data."""
        result = _extract_user_info({})
        assert result == {}

    @pytest.mark.parametrize(
        "field,value,expected_key",
        [
            ("active", False, "active"),
            ("verified", False, "verified"),
            ("active", True, "active"),
            ("verified", True, "verified"),
        ],
    )
    def test_extract_boolean_fields(self, field, value, expected_key):
        """Test extracting boolean fields correctly."""
        user_data = {field: value}
        result = _extract_user_info(user_data)
        assert result[expected_key] == value


class TestExtractOrganizationInfo:
    """Test the _extract_organization_info function."""

    def test_extract_complete_organization_info(self, sample_organization_data):
        """Test extracting complete organization information."""
        result = _extract_organization_info(sample_organization_data)

        assert result["organization_name"] == "Example Corp"
        assert result["organization_domains"] == ["example.com", "example.org"]

    def test_extract_organization_info_no_domains(self):
        """Test extracting organization info without domain names."""
        org_data = {
            "name": "Example Corp",
            "domain_names": [],
        }

        result = _extract_organization_info(org_data)

        assert result["organization_name"] == "Example Corp"
        assert "organization_domains" not in result

    def test_extract_organization_info_multiple_domains(self):
        """Test extracting organization info with multiple domains."""
        org_data = {
            "name": "Example Corp",
            "domain_names": ["primary.com", "secondary.com", "tertiary.com"],
        }

        result = _extract_organization_info(org_data)

        assert result["organization_name"] == "Example Corp"
        assert result["organization_domains"] == ["primary.com", "secondary.com", "tertiary.com"]

    def test_extract_empty_organization_info(self):
        """Test extracting from empty organization data."""
        result = _extract_organization_info({})
        assert "organization_name" not in result
        assert "organization_domains" not in result
        assert result == {}


class TestWhoAmIResponseType:
    """Test the WhoAmIResponse TypedDict."""

    def test_typed_dict_structure(self):
        """Test that WhoAmIResponse accepts expected fields."""
        response: WhoAmIResponse = {
            "user_id": 12345,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "role": "admin",
            "active": True,
            "verified": True,
            "locale": "en-US",
            "time_zone": "America/New_York",
            "organization_id": 67890,
            "organization_name": "Example Corp",
            "organization_domains": ["example.com", "example.org"],
            "zendesk_access": True,
        }

        assert response["user_id"] == 12345
        assert response["zendesk_access"] is True

    def test_typed_dict_partial(self):
        """Test that WhoAmIResponse works with partial data."""
        response: WhoAmIResponse = {
            "user_id": 12345,
            "name": "John Doe",
            "zendesk_access": True,
        }

        assert response["user_id"] == 12345
        assert response["zendesk_access"] is True
