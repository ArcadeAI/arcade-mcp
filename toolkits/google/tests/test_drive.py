from unittest.mock import AsyncMock, patch

import pytest
from arcade_tdk.errors import ToolExecutionError
from googleapiclient.errors import HttpError

from arcade_google.models import Corpora, DocumentFormat, OrderBy
from arcade_google.tools import (
    get_file_tree_structure,
    search_and_retrieve_documents,
    search_documents,
)
from arcade_google.utils import build_drive_service


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
@patch("arcade_google.tools.drive.search_documents")
@patch("arcade_google.tools.drive.get_document_by_id")
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
    result = await search_and_retrieve_documents(
        mock_context,
        document_contains=[sample_document["title"]],
        return_format=DocumentFormat.MARKDOWN,
    )
    assert result["documents_count"] == 1
    assert result["documents"][0] == expected_markdown


@pytest.mark.asyncio
@patch("arcade_google.tools.drive.search_documents")
@patch("arcade_google.tools.drive.get_document_by_id")
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
    result = await search_and_retrieve_documents(
        mock_context,
        document_contains=[sample_document["title"]],
        return_format=DocumentFormat.HTML,
    )
    assert result["documents_count"] == 1
    assert result["documents"][0] == expected_html


@pytest.mark.asyncio
@patch("arcade_google.tools.drive.search_documents")
@patch("arcade_google.tools.drive.get_document_by_id")
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
    result = await search_and_retrieve_documents(
        mock_context,
        document_contains=[sample_document["title"]],
        return_format=DocumentFormat.GOOGLE_API_JSON,
    )
    assert result["documents_count"] == 1
    assert result["documents"][0] == sample_document


@pytest.mark.asyncio
async def test_get_file_tree_structure(
    mock_context, mock_service, sample_drive_file_tree_request_responses
):
    files_list_sample, drives_get_sample = sample_drive_file_tree_request_responses

    mock_service.files.return_value.list.return_value.execute.side_effect = [files_list_sample]
    mock_service.drives.return_value.get.return_value.execute.side_effect = drives_get_sample

    result = await get_file_tree_structure(mock_context, include_shared_drives=True)

    expected_file_tree = {
        "drives": [
            {
                "id": "0AFqcR6obkydtUk9PVA",
                "name": "Shared Drive 1",
                "children": [
                    {
                        "createdTime": "2025-02-26T00:27:45.526Z",
                        "id": "1dCOCdPxhTqiB3j3bWrIWM692ZbL8dyjt",
                        "mimeType": "application/vnd.google-apps.folder",
                        "modifiedTime": "2025-02-26T00:27:45.526Z",
                        "name": "shared-1-folder-1",
                        "children": [
                            {
                                "createdTime": "2025-02-26T00:28:20.571Z",
                                "id": "19WVyQndQsc0AxxfdrIt5CvDQd6r-BvpqnB8bWZoL7Xk",
                                "mimeType": "application/vnd.google-apps.document",
                                "modifiedTime": "2025-02-26T00:28:30.773Z",
                                "name": "shared-1-folder-1-doc-1",
                                "size": {
                                    "unit": "bytes",
                                    "value": 1024,
                                },
                            }
                        ],
                    },
                    {
                        "createdTime": "2025-02-26T00:27:19.287Z",
                        "id": "1didt_h-tDjuJ-dmYtHUSyOCPci30K_kSszvg0G3tKBM",
                        "mimeType": "application/vnd.google-apps.document",
                        "modifiedTime": "2025-02-26T00:27:26.079Z",
                        "name": "shared-1-doc-1",
                        "size": {
                            "unit": "bytes",
                            "value": 1024,
                        },
                    },
                ],
            },
            {
                "name": "My Drive",
                "children": [
                    {
                        "createdTime": "2025-01-24T06:34:22.305Z",
                        "id": "1vB6sv0MD0hYSraYvWU_fcci3GN_-Jf4g-LfyXdG8ZMo",
                        "mimeType": "application/vnd.google-apps.document",
                        "modifiedTime": "2025-02-25T21:54:30.632Z",
                        "name": "The Birth of MX Engineering",
                        "owners": [
                            {
                                "email": "one_new_tool_everyday@arcade.dev",
                                "name": "one_new_tool_everyday",
                            }
                        ],
                        "size": {
                            "unit": "bytes",
                            "value": 6634,
                        },
                    },
                    {
                        "createdTime": "2025-02-25T17:57:46.036Z",
                        "id": "1gqioaHG53jPVeJN5gBpHoO-GWtwiJcLo",
                        "mimeType": "application/vnd.google-apps.folder",
                        "modifiedTime": "2025-02-25T17:57:46.036Z",
                        "name": "test folder 1",
                        "owners": [
                            {
                                "email": "one_new_tool_everyday@arcade.dev",
                                "name": "one_new_tool_everyday",
                            }
                        ],
                        "children": [
                            {
                                "id": "1J92V9yvVWm_uNHq3CCY4wyG1H9B6iiwO",
                                "name": "test folder 1.1",
                                "mimeType": "application/vnd.google-apps.folder",
                                "createdTime": "2025-02-25T17:58:58.987Z",
                                "modifiedTime": "2025-02-25T17:58:58.987Z",
                                "owners": [
                                    {
                                        "email": "one_new_tool_everyday@arcade.dev",
                                        "name": "one_new_tool_everyday",
                                    }
                                ],
                                "children": [
                                    {
                                        "id": "1wv2dmYo0skJTI59ZIcwH9vm-wt7psMwXTvihuEGeHeI",
                                        "name": "test document 1.1.1",
                                        "mimeType": "application/vnd.google-apps.document",
                                        "createdTime": "2025-02-25T17:59:03.325Z",
                                        "modifiedTime": "2025-02-25T17:59:11.445Z",
                                        "owners": [
                                            {
                                                "email": "one_new_tool_everyday@arcade.dev",
                                                "name": "one_new_tool_everyday",
                                            }
                                        ],
                                        "size": {
                                            "unit": "bytes",
                                            "value": 1024,
                                        },
                                    },
                                ],
                            },
                            {
                                "id": "1DSmL7d07kjT6b6L-t4JIT06ElUbZ1q0K6_gEpn_UGZ8",
                                "name": "test document 1.2",
                                "mimeType": "application/vnd.google-apps.document",
                                "createdTime": "2025-02-25T17:58:38.628Z",
                                "modifiedTime": "2025-02-25T17:58:46.713Z",
                                "owners": [
                                    {
                                        "email": "one_new_tool_everyday@arcade.dev",
                                        "name": "one_new_tool_everyday",
                                    }
                                ],
                                "size": {
                                    "unit": "bytes",
                                    "value": 1024,
                                },
                            },
                            {
                                "id": "1Fcxz7HsyO2Zyc-5DTD3zBQnaVrZwD29BP9KD9rPnYfE",
                                "name": "test document 1.1",
                                "mimeType": "application/vnd.google-apps.document",
                                "createdTime": "2025-02-25T17:57:53.850Z",
                                "modifiedTime": "2025-02-25T17:58:28.745Z",
                                "owners": [
                                    {
                                        "email": "one_new_tool_everyday@arcade.dev",
                                        "name": "one_new_tool_everyday",
                                    }
                                ],
                                "size": {
                                    "unit": "bytes",
                                    "value": 1024,
                                },
                            },
                        ],
                    },
                    {
                        "createdTime": "2025-02-18T20:48:52.786Z",
                        "id": "16PUe97yGQeOjQgrgd54iCoxzid4SEvu_J33P_ELd5r8",
                        "mimeType": "application/vnd.google-apps.presentation",
                        "modifiedTime": "2025-02-19T23:31:20.483Z",
                        "name": "Hello world presentation",
                        "owners": [
                            {
                                "email": "john.doe@arcade.dev",
                                "name": "john.doe",
                            }
                        ],
                        "size": {
                            "unit": "bytes",
                            "value": 15774558,
                        },
                    },
                    {
                        "id": "1nG7lSvIyK05N9METPczVJa4iGgE7uoo-A6zpqjpUsDY",
                        "name": "Shared doc 1",
                        "mimeType": "application/vnd.google-apps.document",
                        "createdTime": "2025-02-19T18:51:44.622Z",
                        "modifiedTime": "2025-02-19T19:30:39.773Z",
                        "owners": [
                            {
                                "name": "theboss",
                                "email": "theboss@arcade.dev",
                            }
                        ],
                        "size": {
                            "unit": "bytes",
                            "value": 2700,
                        },
                    },
                ],
            },
        ]
    }

    assert result == expected_file_tree
