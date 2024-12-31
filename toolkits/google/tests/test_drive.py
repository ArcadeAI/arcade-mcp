from unittest.mock import AsyncMock, patch

import pytest
from arcade.sdk.errors import ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_google.tools.drive import list_documents
from arcade_google.tools.models import Corpora, OrderBy
from arcade_google.tools.utils import build_drive_service


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "mock_token"  # noqa: S105
    return context


@pytest.fixture
def mock_service():
    with patch("arcade_google.tools.drive." + build_drive_service.__name__) as mock_build_service:
        yield mock_build_service.return_value


@pytest.mark.asyncio
async def test_list_documents_success(mock_context, mock_service):
    # Mock the service.files().list().execute() method
    mock_service.files.return_value.list.return_value.execute.side_effect = [
        {
            "files": [
                {"id": "file1", "name": "Document 1"},
                {"id": "file2", "name": "Document 2"},
            ],
            "nextPageToken": None,
        }
    ]

    result = await list_documents(mock_context, limit=2)

    assert result["documents_count"] == 2
    assert len(result["documents"]) == 2
    assert result["documents"][0]["id"] == "file1"
    assert result["documents"][1]["id"] == "file2"


@pytest.mark.asyncio
async def test_list_documents_pagination(mock_context, mock_service):
    # Simulate multiple pages
    mock_service.files.return_value.list.return_value.execute.side_effect = [
        {
            "files": [{"id": f"file{i}", "name": f"Document {i}"} for i in range(1, 11)],
            "nextPageToken": "token1",
        },
        {
            "files": [{"id": f"file{i}", "name": f"Document {i}"} for i in range(11, 21)],
            "nextPageToken": None,
        },
    ]

    result = await list_documents(mock_context, limit=15)

    assert result["documents_count"] == 15
    assert len(result["documents"]) == 15
    assert result["documents"][0]["id"] == "file1"
    assert result["documents"][-1]["id"] == "file15"


@pytest.mark.asyncio
async def test_list_documents_http_error(mock_context, mock_service):
    # Simulate HttpError
    mock_service.files.return_value.list.return_value.execute.side_effect = HttpError(
        resp=AsyncMock(status=403), content=b'{"error": {"message": "Forbidden"}}'
    )

    with pytest.raises(ToolExecutionError, match="Error in execution of ListDocuments"):
        await list_documents(mock_context)


@pytest.mark.asyncio
async def test_list_documents_unexpected_error(mock_context, mock_service):
    # Simulate unexpected exception
    mock_service.files.return_value.list.return_value.execute.side_effect = Exception(
        "Unexpected error"
    )

    with pytest.raises(ToolExecutionError, match="Error in execution of ListDocuments"):
        await list_documents(mock_context)


@pytest.mark.asyncio
async def test_list_documents_with_parameters(mock_context, mock_service):
    # Mock the service.files().list().execute() method
    mock_service.files.return_value.list.return_value.execute.side_effect = [
        {
            "files": [
                {"id": "file1", "name": "Document 1"},
            ],
            "nextPageToken": None,
        }
    ]

    result = await list_documents(
        mock_context,
        corpora=Corpora.USER,
        order_by=OrderBy.MODIFIED_TIME_DESC,
        supports_all_drives=False,
        limit=1,
    )

    assert result["documents_count"] == 1
    mock_service.files.return_value.list.assert_called_with(
        q="mimeType = 'application/vnd.google-apps.document' and trashed = false",
        pageSize=1,
        orderBy="modifiedTime desc",
        corpora="user",
        supportsAllDrives=False,
    )
