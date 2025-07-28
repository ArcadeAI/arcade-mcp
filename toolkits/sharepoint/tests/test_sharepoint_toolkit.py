"""Comprehensive tests for the SharePoint toolkit."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from arcade_tdk import ToolContext

# Import all the tools we want to test
from arcade_sharepoint.tools.sites import list_sites, get_site, search_sites, get_followed_sites
from arcade_sharepoint.tools.drives import list_site_drives, get_site_default_drive, get_drive, get_user_drives, search_drives
from arcade_sharepoint.tools.documents import list_drive_items, get_drive_item, search_drive_items, get_recent_files, get_file_versions
from arcade_sharepoint.tools.search import search_sharepoint, search_documents, search_by_author, search_recent_content

# Test data
MOCK_SITE_ID = "contoso.sharepoint.com,123e4567-e89b-12d3-a456-426614174000,987fcdeb-51a2-43d1-876b-987fcdeb51a2"
MOCK_DRIVE_ID = "b!A6LbyYCrTU2xN0Nr4_mmuJtEgTeaoxNCsRlb21z5NHIrJX3-S0XxRKSt_SQpo-T4"
MOCK_ITEM_ID = "01A6LBYYQCRR7XBGZ3B5HKQ2TKWXVJYMNM"

@pytest.fixture
def mock_context():
    """Create a mock ToolContext for testing."""
    context = MagicMock(spec=ToolContext)
    context.get_auth_token_or_empty.return_value = "mock_token_123"
    return context

@pytest.fixture
def mock_client():
    """Create a mock Graph client."""
    client = MagicMock()
    return client

class TestSiteTools:
    """Test site-related tools."""
    
    @pytest.mark.asyncio
    async def test_list_sites_success(self, mock_context):
        """Test successful listing of sites."""
        with patch('arcade_sharepoint.tools.sites.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock response
            mock_response = MagicMock()
            mock_response.value = [
                MagicMock(
                    id=MOCK_SITE_ID,
                    display_name="Test Site",
                    web_url="https://contoso.sharepoint.com/sites/test",
                    created_date_time="2023-01-01T00:00:00Z"
                )
            ]
            mock_client.sites.get.return_value = mock_response
            
            result = await list_sites(mock_context, limit=10)
            
            assert result["count"] == 1
            assert result["sites"][0]["display_name"] == "Test Site"
            assert "pagination" in result

class TestDriveTools:
    """Test drive-related tools."""
    
    @pytest.mark.asyncio
    async def test_list_site_drives_success(self, mock_context):
        """Test successful listing of site drives."""
        with patch('arcade_sharepoint.tools.drives.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock response
            mock_response = MagicMock()
            mock_response.value = [
                MagicMock(
                    id=MOCK_DRIVE_ID,
                    name="Documents",
                    drive_type="documentLibrary",
                    web_url="https://contoso.sharepoint.com/sites/test/Shared%20Documents"
                )
            ]
            mock_client.sites.by_site_id.return_value.drives.get.return_value = mock_response
            
            result = await list_site_drives(mock_context, MOCK_SITE_ID)
            
            assert result["count"] == 1
            assert result["drives"][0]["name"] == "Documents"

    @pytest.mark.asyncio
    async def test_get_drive_success(self, mock_context):
        """Test successful drive retrieval."""
        with patch('arcade_sharepoint.tools.drives.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock drive response
            mock_drive = MagicMock(
                id=MOCK_DRIVE_ID,
                name="Documents",
                drive_type="documentLibrary"
            )
            mock_client.drives.by_drive_id.return_value.get.return_value = mock_drive
            
            result = await get_drive(mock_context, MOCK_DRIVE_ID)
            
            assert result["drive"]["name"] == "Documents"
            assert "error" not in result

class TestDocumentTools:
    """Test document-related tools."""
    
    @pytest.mark.asyncio
    async def test_list_drive_items_success(self, mock_context):
        """Test successful listing of drive items."""
        with patch('arcade_sharepoint.tools.documents.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock response
            mock_response = MagicMock()
            mock_response.value = [
                MagicMock(
                    id=MOCK_ITEM_ID,
                    name="test_file.docx",
                    size=1024,
                    web_url="https://contoso.sharepoint.com/sites/test/Shared%20Documents/test_file.docx",
                    file=MagicMock(),  # Indicates it's a file
                    folder=None
                )
            ]
            mock_client.drives.by_drive_id.return_value.items.by_drive_item_id.return_value.children.get.return_value = mock_response
            
            result = await list_drive_items(mock_context, MOCK_DRIVE_ID, "/")
            
            assert result["count"] == 1
            assert result["items"][0]["name"] == "test_file.docx"
            assert result["drive_id"] == MOCK_DRIVE_ID

    @pytest.mark.asyncio
    async def test_get_drive_item_success(self, mock_context):
        """Test successful drive item retrieval."""
        with patch('arcade_sharepoint.tools.documents.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock item response
            mock_item = MagicMock(
                id=MOCK_ITEM_ID,
                name="test_file.docx",
                size=1024
            )
            mock_client.drives.by_drive_id.return_value.items.by_drive_item_id.return_value.get.return_value = mock_item
            
            result = await get_drive_item(mock_context, MOCK_DRIVE_ID, MOCK_ITEM_ID)
            
            assert result["item"]["name"] == "test_file.docx"
            assert result["drive_id"] == MOCK_DRIVE_ID

class TestSearchTools:
    """Test search-related tools."""
    
    @pytest.mark.asyncio
    async def test_search_sharepoint_success(self, mock_context):
        """Test successful SharePoint search."""
        with patch('arcade_sharepoint.tools.search.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock search response
            mock_response = MagicMock()
            mock_response.value = [MagicMock(hits_containers=[MagicMock(hits=[
                MagicMock(resource=MagicMock(id="123", name="test result"))
            ])])]
            mock_client.search.query.post.return_value = mock_response
            
            result = await search_sharepoint(mock_context, "test query")
            
            assert result["count"] >= 0
            assert "search_term" in result

    @pytest.mark.asyncio
    async def test_search_documents_with_file_type(self, mock_context):
        """Test document search with file type filter."""
        with patch('arcade_sharepoint.tools.search.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock search response
            mock_response = MagicMock()
            mock_response.value = [MagicMock(hits_containers=[MagicMock(hits=[])])]
            mock_client.search.query.post.return_value = mock_response
            
            result = await search_documents(mock_context, "test", file_type="pdf")
            
            assert result["file_type"] == "pdf"
            assert result["search_term"] == "test"

class TestInputValidation:
    """Test input validation scenarios."""
    
    @pytest.mark.asyncio
    async def test_negative_limit_parameter(self, mock_context):
        """Test handling of negative limit parameter."""
        # The function should handle this gracefully by setting minimum limit
        with patch('arcade_sharepoint.tools.sites.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.value = []
            mock_client.sites.get.return_value = mock_response
            
            result = await list_sites(mock_context, limit=-5)
            
            # Should not error, should use minimum limit of 1
            assert "sites" in result

    @pytest.mark.asyncio
    async def test_excessive_limit_parameter(self, mock_context):
        """Test handling of excessive limit parameter."""
        with patch('arcade_sharepoint.tools.sites.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.value = []
            mock_client.sites.get.return_value = mock_response
            
            result = await list_sites(mock_context, limit=1000)
            
            # Should not error, should use maximum limit of 50
            assert "sites" in result

class TestPagination:
    """Test pagination functionality."""
    
    @pytest.mark.asyncio
    async def test_pagination_with_more_results(self, mock_context):
        """Test pagination when more results are available."""
        with patch('arcade_sharepoint.tools.sites.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # Mock response with exactly the limit (indicates more results available)
            mock_response = MagicMock()
            mock_response.value = [MagicMock() for _ in range(25)]  # Default limit
            mock_client.sites.get.return_value = mock_response
            
            result = await list_sites(mock_context, limit=25)
            
            assert "pagination" in result
            # Check pagination structure
            pagination = result["pagination"]
            assert "has_more" in pagination
            assert "next_offset" in pagination

class TestSpecialCharacters:
    """Test handling of special characters in paths and names."""
    
    @pytest.mark.asyncio
    async def test_path_with_special_characters(self, mock_context):
        """Test handling of paths with special characters."""
        special_path = "/Documents/My Files/#special folder"
        
        with patch('arcade_sharepoint.tools.documents.get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_response = MagicMock()
            mock_response.value = []
            mock_client.drives.by_drive_id.return_value.items.by_drive_item_id.return_value.children.get.return_value = mock_response
            
            result = await list_drive_items(mock_context, MOCK_DRIVE_ID, special_path)
            
            # Should handle special characters without error
            assert "items" in result

class TestImportStructure:
    """Test that all expected functions are importable."""
    
    def test_sites_tools_importable(self):
        """Test that sites tools can be imported."""
        from arcade_sharepoint.tools.sites import list_sites, get_site, search_sites, get_followed_sites
        assert callable(list_sites)
        assert callable(get_site)
        assert callable(search_sites)
        assert callable(get_followed_sites)
    
    def test_drives_tools_importable(self):
        """Test that drives tools can be imported."""
        from arcade_sharepoint.tools.drives import list_site_drives, get_site_default_drive, get_drive, get_user_drives, search_drives
        assert callable(list_site_drives)
        assert callable(get_site_default_drive)
        assert callable(get_drive)
        assert callable(get_user_drives)
        assert callable(search_drives)
    
    def test_documents_tools_importable(self):
        """Test that documents tools can be imported."""
        from arcade_sharepoint.tools.documents import list_drive_items, get_drive_item, search_drive_items, get_recent_files, get_file_versions
        assert callable(list_drive_items)
        assert callable(get_drive_item)
        assert callable(search_drive_items)
        assert callable(get_recent_files)
        assert callable(get_file_versions)
    
    def test_search_tools_importable(self):
        """Test that search tools can be imported."""
        from arcade_sharepoint.tools.search import search_sharepoint, search_documents, search_by_author, search_recent_content
        assert callable(search_sharepoint)
        assert callable(search_documents)
        assert callable(search_by_author)
        assert callable(search_recent_content)

if __name__ == "__main__":
    pytest.main([__file__]) 