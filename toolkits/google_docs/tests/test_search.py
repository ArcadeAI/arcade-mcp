from unittest.mock import AsyncMock, patch

import pytest
from arcade_tdk.errors import ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_google_docs.enum import Corpora, DocumentFormat, OrderBy
from arcade_google_docs.templates import optional_file_picker_instructions_template
from arcade_google_docs.tools import (
    search_and_retrieve_documents,
    search_documents,
)
from arcade_google_docs.utils import build_drive_service


@pytest.fixture
def mock_context():
    context = AsyncMock()
    context.authorization.token = "mock_token"  # noqa: S105
    context.get_metadata.side_effect = lambda key: {
        "client_id": "123456789-abcdefg.apps.googleusercontent.com",
        "coordinator_url": "https://coordinator.example.com",
    }.get(key.value if hasattr(key, "value") else key)
    return context


@pytest.fixture
def mock_service():
    with patch(
        "arcade_google_docs.tools.search." + build_drive_service.__name__
    ) as mock_build_service:
        yield mock_build_service.return_value


@pytest.mark.asyncio
async def test_search_documents_success(mock_context, mock_service):
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

    # Mock the generate_google_file_picker_url function
    with patch(
        "arcade_google_docs.tools.search.generate_google_file_picker_url"
    ) as mock_file_picker:
        mock_file_picker.return_value = {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        }

        result = await search_documents(mock_context, limit=2)

    assert result["documents_count"] == 2
    assert len(result["documents"]) == 2
    assert result["documents"][0]["id"] == "file1"
    assert result["documents"][1]["id"] == "file2"


@pytest.mark.asyncio
async def test_search_documents_pagination(mock_context, mock_service):
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

    # Mock the generate_google_file_picker_url function
    with patch(
        "arcade_google_docs.tools.search.generate_google_file_picker_url"
    ) as mock_file_picker:
        mock_file_picker.return_value = {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        }

        result = await search_documents(mock_context, limit=15)

    assert result["documents_count"] == 15
    assert len(result["documents"]) == 15
    assert result["documents"][0]["id"] == "file1"
    assert result["documents"][-1]["id"] == "file15"


@pytest.mark.asyncio
async def test_search_documents_http_error(mock_context, mock_service):
    # Simulate HttpError
    mock_service.files.return_value.list.return_value.execute.side_effect = HttpError(
        resp=AsyncMock(status=403), content=b'{"error": {"message": "Forbidden"}}'
    )

    with pytest.raises(
        ToolExecutionError, match=f"Error in execution of {search_documents.__tool_name__}"
    ):
        await search_documents(mock_context)


@pytest.mark.asyncio
async def test_search_documents_unexpected_error(mock_context, mock_service):
    # Simulate unexpected exception
    mock_service.files.return_value.list.return_value.execute.side_effect = Exception(
        "Unexpected error"
    )

    with pytest.raises(
        ToolExecutionError, match=f"Error in execution of {search_documents.__tool_name__}"
    ):
        await search_documents(mock_context)


@pytest.mark.asyncio
async def test_search_documents_in_organization_domains(mock_context, mock_service):
    # Mock the service.files().list().execute() method
    mock_service.files.return_value.list.return_value.execute.side_effect = [
        {
            "files": [
                {"id": "file1", "name": "Document 1"},
            ],
            "nextPageToken": None,
        }
    ]

    # Mock the generate_google_file_picker_url function
    with patch(
        "arcade_google_docs.tools.search.generate_google_file_picker_url"
    ) as mock_file_picker:
        mock_file_picker.return_value = {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        }

        result = await search_documents(
            mock_context,
            order_by=OrderBy.MODIFIED_TIME_DESC,
            include_shared_drives=False,
            include_organization_domain_documents=True,
            limit=1,
        )

    assert result["documents_count"] == 1
    mock_service.files.return_value.list.assert_called_with(
        q="(mimeType = 'application/vnd.google-apps.document' and trashed = false)",
        corpora=Corpora.DOMAIN.value,
        pageSize=1,
        orderBy=OrderBy.MODIFIED_TIME_DESC.value,
        includeItemsFromAllDrives="true",
        supportsAllDrives="true",
    )


@pytest.mark.asyncio
@patch("arcade_google_docs.tools.search.search_documents")
@patch("arcade_google_docs.tools.search.get_document_by_id")
async def test_search_and_retrieve_documents_in_markdown_format(
    mock_get_document_by_id,
    mock_search_documents,
    mock_context,
    sample_document_and_expected_formats,
):
    (sample_document, expected_markdown, _) = sample_document_and_expected_formats
    mock_search_documents.return_value = {
        "documents_count": 1,
        "documents": [{"id": sample_document["documentId"], "title": sample_document["title"]}],
    }
    mock_get_document_by_id.return_value = sample_document

    # Mock the generate_google_file_picker_url function
    with patch(
        "arcade_google_docs.tools.search.generate_google_file_picker_url"
    ) as mock_file_picker:
        mock_file_picker.return_value = {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        }

        result = await search_and_retrieve_documents(
            mock_context,
            document_contains=[sample_document["title"]],
            return_format=DocumentFormat.MARKDOWN,
        )

    assert result["documents_count"] == 1
    assert result["documents"][0] == expected_markdown


@pytest.mark.asyncio
@patch("arcade_google_docs.tools.search.search_documents")
@patch("arcade_google_docs.tools.search.get_document_by_id")
async def test_search_and_retrieve_documents_in_html_format(
    mock_get_document_by_id,
    mock_search_documents,
    mock_context,
    sample_document_and_expected_formats,
):
    (sample_document, _, expected_html) = sample_document_and_expected_formats
    mock_search_documents.return_value = {
        "documents_count": 1,
        "documents": [{"id": sample_document["documentId"], "title": sample_document["title"]}],
    }
    mock_get_document_by_id.return_value = sample_document

    # Mock the generate_google_file_picker_url function
    with patch(
        "arcade_google_docs.tools.search.generate_google_file_picker_url"
    ) as mock_file_picker:
        mock_file_picker.return_value = {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        }

        result = await search_and_retrieve_documents(
            mock_context,
            document_contains=[sample_document["title"]],
            return_format=DocumentFormat.HTML,
        )

    assert result["documents_count"] == 1
    assert result["documents"][0] == expected_html


@pytest.mark.asyncio
@patch("arcade_google_docs.tools.search.search_documents")
@patch("arcade_google_docs.tools.search.get_document_by_id")
async def test_search_and_retrieve_documents_in_google_json_format(
    mock_get_document_by_id,
    mock_search_documents,
    mock_context,
    sample_document_and_expected_formats,
):
    (sample_document, _, _) = sample_document_and_expected_formats
    mock_search_documents.return_value = {
        "documents_count": 1,
        "documents": [{"id": sample_document["documentId"], "title": sample_document["title"]}],
    }
    mock_get_document_by_id.return_value = sample_document

    # Mock the generate_google_file_picker_url function
    with patch(
        "arcade_google_docs.tools.search.generate_google_file_picker_url"
    ) as mock_file_picker:
        mock_file_picker.return_value = {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        }

        result = await search_and_retrieve_documents(
            mock_context,
            document_contains=[sample_document["title"]],
            return_format=DocumentFormat.GOOGLE_API_JSON,
        )

    assert result["documents_count"] == 1
    assert result["documents"][0] == sample_document
