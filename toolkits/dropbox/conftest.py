from unittest.mock import patch

import pytest
from arcade_tdk import ToolAuthorizationContext, ToolContext


@pytest.fixture
def mock_context():
    mock_auth = ToolAuthorizationContext(token="fake-token")  # noqa: S106
    return ToolContext(authorization=mock_auth)


@pytest.fixture
def mock_httpx_client(mocker):
    with patch("arcade_dropbox.utils.httpx") as mock_httpx:
        yield mock_httpx.AsyncClient().__aenter__.return_value


@pytest.fixture
def sample_folder_entry():
    return {
        ".tag": "folder",
        "name": "test.txt",
        "path_display": "/TestFolder",
        "path_lower": "/testfolder",
        "id": "1234567890",
        "client_modified": "2025-01-01T00:00:00Z",
        "server_modified": "2025-01-01T00:00:00Z",
        "rev": "1234567890",
    }


@pytest.fixture
def sample_file_entry():
    return {
        ".tag": "file",
        "name": "test.txt",
        "path_display": "/TestFile.txt",
        "path_lower": "/testfile.txt",
        "id": "1234567890",
        "client_modified": "2025-01-01T00:00:00Z",
        "server_modified": "2025-01-01T00:00:00Z",
        "rev": "1234567890",
        "size": 1024,
    }
