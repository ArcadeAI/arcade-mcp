import logging
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from arcade_google_drive.enums import Corpora, OrderBy

## Set up basic configuration for logging to the console with DEBUG level and a specific format.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def build_drive_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a Drive service object.
    """
    auth_token = auth_token or ""
    return build("drive", "v3", credentials=Credentials(auth_token))


def build_file_tree_request_params(
    order_by: list[OrderBy] | None,
    page_token: str | None,
    limit: int | None,
    include_shared_drives: bool,
    restrict_to_shared_drive_id: str | None,
    include_organization_domain_documents: bool,
) -> dict[str, Any]:
    if order_by is None:
        order_by = [OrderBy.MODIFIED_TIME_DESC]
    elif isinstance(order_by, OrderBy):
        order_by = [order_by]

    params = {
        "q": "trashed = false",
        "corpora": Corpora.USER.value,
        "pageToken": page_token,
        "fields": (
            "files(id, name, parents, mimeType, driveId, size, createdTime, modifiedTime, owners)"
        ),
        "orderBy": ",".join([item.value for item in order_by]),
    }

    if limit:
        params["pageSize"] = str(limit)

    if (
        include_shared_drives
        or restrict_to_shared_drive_id
        or include_organization_domain_documents
    ):
        params["includeItemsFromAllDrives"] = "true"
        params["supportsAllDrives"] = "true"

    if restrict_to_shared_drive_id:
        params["driveId"] = restrict_to_shared_drive_id
        params["corpora"] = Corpora.DRIVE.value

    if include_organization_domain_documents:
        params["corpora"] = Corpora.DOMAIN.value

    return params


def build_file_tree(files: dict[str, Any]) -> dict[str, Any]:
    file_tree: dict[str, Any] = {}

    for file in files.values():
        owners = file.get("owners", [])
        if owners:
            owners = [
                {"name": owner.get("displayName", ""), "email": owner.get("emailAddress", "")}
                for owner in owners
            ]
            file["owners"] = owners

        if "size" in file:
            file["size"] = {"value": int(file["size"]), "unit": "bytes"}

        # Although "parents" is a list, a file can only have one parent
        try:
            parent_id = file["parents"][0]
            del file["parents"]
        except (KeyError, IndexError):
            parent_id = None

        # Determine the file's Drive ID
        if "driveId" in file:
            drive_id = file["driveId"]
            del file["driveId"]
        # If a shared drive id is not present, the file is in "My Drive"
        else:
            drive_id = "My Drive"

        if drive_id not in file_tree:
            file_tree[drive_id] = []

        # Root files will have the Drive's id as the parent. If the parent id is not in the files
        # list, the file must be at drive's root
        if parent_id not in files:
            file_tree[drive_id].append(file)

        # Associate the file with its parent
        else:
            if "children" not in files[parent_id]:
                files[parent_id]["children"] = []
            files[parent_id]["children"].append(file)

    return file_tree
