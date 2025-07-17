from unittest.mock import AsyncMock, patch

import pytest

from arcade_google_drive.templates import optional_file_picker_instructions_template
from arcade_google_drive.tools import (
    get_file_tree_structure,
)
from arcade_google_drive.utils import build_drive_service


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
        "arcade_google_drive.tools.drive." + build_drive_service.__name__
    ) as mock_build_service:
        yield mock_build_service.return_value


@pytest.mark.asyncio
async def test_get_file_tree_structure(
    mock_context, mock_service, sample_drive_file_tree_request_responses
):
    files_list_sample, drives_get_sample = sample_drive_file_tree_request_responses

    mock_service.files.return_value.list.return_value.execute.side_effect = [files_list_sample]
    mock_service.drives.return_value.get.return_value.execute.side_effect = drives_get_sample

    # Mock the generate_google_file_picker_url function
    with patch(
        "arcade_google_drive.tools.drive.generate_google_file_picker_url"
    ) as mock_file_picker:
        mock_file_picker.return_value = {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        }

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
        ],
        "file_picker": {
            "url": "https://coordinator.example.com/google/drive_picker?config=test_config",
            "llm_instructions": optional_file_picker_instructions_template.format(
                url="https://coordinator.example.com/google/drive_picker?config=test_config"
            ),
        },
    }

    assert result == expected_file_tree
