import pytest


@pytest.fixture
def sample_drive_file_tree_request_responses() -> tuple[dict, list]:
    files_list = {
        "files": [
            # Shared Drive 1 files and folders
            {
                "id": "19WVyQndQsc0AxxfdrIt5CvDQd6r-BvpqnB8bWZoL7Xk",
                "name": "shared-1-folder-1-doc-1",
                "mimeType": "application/vnd.google-apps.document",
                "parents": ["1dCOCdPxhTqiB3j3bWrIWM692ZbL8dyjt"],
                "createdTime": "2025-02-26T00:28:20.571Z",
                "modifiedTime": "2025-02-26T00:28:30.773Z",
                "driveId": "0AFqcR6obkydtUk9PVA",
                "size": "1024",
            },
            {
                "id": "1dCOCdPxhTqiB3j3bWrIWM692ZbL8dyjt",
                "name": "shared-1-folder-1",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": ["0AFqcR6obkydtUk9PVA"],
                "createdTime": "2025-02-26T00:27:45.526Z",
                "modifiedTime": "2025-02-26T00:27:45.526Z",
                "driveId": "0AFqcR6obkydtUk9PVA",
            },
            {
                "id": "1didt_h-tDjuJ-dmYtHUSyOCPci30K_kSszvg0G3tKBM",
                "name": "shared-1-doc-1",
                "mimeType": "application/vnd.google-apps.document",
                "parents": ["0AFqcR6obkydtUk9PVA"],
                "createdTime": "2025-02-26T00:27:19.287Z",
                "modifiedTime": "2025-02-26T00:27:26.079Z",
                "driveId": "0AFqcR6obkydtUk9PVA",
                "size": "1024",
            },
            # My Drive files and folders
            {
                "id": "1vB6sv0MD0hYSraYvWU_fcci3GN_-Jf4g-LfyXdG8ZMo",
                "name": "The Birth of MX Engineering",
                "mimeType": "application/vnd.google-apps.document",
                "parents": ["0AIbBwO2hjeHqUk9PVA"],
                "createdTime": "2025-01-24T06:34:22.305Z",
                "modifiedTime": "2025-02-25T21:54:30.632Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "one_new_tool_everyday",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": True,
                        "permissionId": "00356981722324419750",
                        "emailAddress": "one_new_tool_everyday@arcade.dev",
                    }
                ],
                "size": "6634",
            },
            {
                "id": "1wv2dmYo0skJTI59ZIcwH9vm-wt7psMwXTvihuEGeHeI",
                "name": "test document 1.1.1",
                "mimeType": "application/vnd.google-apps.document",
                "parents": ["1J92V9yvVWm_uNHq3CCY4wyG1H9B6iiwO"],
                "createdTime": "2025-02-25T17:59:03.325Z",
                "modifiedTime": "2025-02-25T17:59:11.445Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "one_new_tool_everyday",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": True,
                        "permissionId": "00356981722324419750",
                        "emailAddress": "one_new_tool_everyday@arcade.dev",
                    }
                ],
                "size": "1024",
            },
            {
                "id": "1J92V9yvVWm_uNHq3CCY4wyG1H9B6iiwO",
                "name": "test folder 1.1",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": ["1gqioaHG53jPVeJN5gBpHoO-GWtwiJcLo"],
                "createdTime": "2025-02-25T17:58:58.987Z",
                "modifiedTime": "2025-02-25T17:58:58.987Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "one_new_tool_everyday",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": True,
                        "permissionId": "00356981722324419750",
                        "emailAddress": "one_new_tool_everyday@arcade.dev",
                    }
                ],
            },
            {
                "id": "1DSmL7d07kjT6b6L-t4JIT06ElUbZ1q0K6_gEpn_UGZ8",
                "name": "test document 1.2",
                "mimeType": "application/vnd.google-apps.document",
                "parents": ["1gqioaHG53jPVeJN5gBpHoO-GWtwiJcLo"],
                "createdTime": "2025-02-25T17:58:38.628Z",
                "modifiedTime": "2025-02-25T17:58:46.713Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "one_new_tool_everyday",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": True,
                        "permissionId": "00356981722324419750",
                        "emailAddress": "one_new_tool_everyday@arcade.dev",
                    }
                ],
                "size": "1024",
            },
            {
                "id": "1Fcxz7HsyO2Zyc-5DTD3zBQnaVrZwD29BP9KD9rPnYfE",
                "name": "test document 1.1",
                "mimeType": "application/vnd.google-apps.document",
                "parents": ["1gqioaHG53jPVeJN5gBpHoO-GWtwiJcLo"],
                "createdTime": "2025-02-25T17:57:53.850Z",
                "modifiedTime": "2025-02-25T17:58:28.745Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "one_new_tool_everyday",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": True,
                        "permissionId": "00356981722324419750",
                        "emailAddress": "one_new_tool_everyday@arcade.dev",
                    }
                ],
                "size": "1024",
            },
            {
                "id": "1gqioaHG53jPVeJN5gBpHoO-GWtwiJcLo",
                "name": "test folder 1",
                "mimeType": "application/vnd.google-apps.folder",
                "parents": ["0AIbBwO2hjeHqUk9PVA"],
                "createdTime": "2025-02-25T17:57:46.036Z",
                "modifiedTime": "2025-02-25T17:57:46.036Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "one_new_tool_everyday",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": True,
                        "permissionId": "00356981722324419750",
                        "emailAddress": "one_new_tool_everyday@arcade.dev",
                    }
                ],
            },
            {
                "id": "16PUe97yGQeOjQgrgd54iCoxzid4SEvu_J33P_ELd5r8",
                "name": "Hello world presentation",
                "mimeType": "application/vnd.google-apps.presentation",
                "createdTime": "2025-02-18T20:48:52.786Z",
                "modifiedTime": "2025-02-19T23:31:20.483Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "john.doe",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": False,
                        "permissionId": "06420661154928749996",
                        "emailAddress": "john.doe@arcade.dev",
                    }
                ],
                "size": "15774558",
            },
            {
                "id": "1nG7lSvIyK05N9METPczVJa4iGgE7uoo-A6zpqjpUsDY",
                "name": "Shared doc 1",
                "mimeType": "application/vnd.google-apps.document",
                "createdTime": "2025-02-19T18:51:44.622Z",
                "modifiedTime": "2025-02-19T19:30:39.773Z",
                "owners": [
                    {
                        "kind": "drive#user",
                        "displayName": "theboss",
                        "photoLink": "https://lh3.googleusercontent.com/a-/photo.png",
                        "me": False,
                        "permissionId": "11571864250637401873",
                        "emailAddress": "theboss@arcade.dev",
                    }
                ],
                "size": "2700",
            },
        ],
    }

    drives_get = [
        {
            "id": "0AFqcR6obkydtUk9PVA",
            "name": "Shared Drive 1",
        }
    ]

    return files_list, drives_get
