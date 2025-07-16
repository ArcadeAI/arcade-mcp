from typing import Annotated

from arcade_tdk import ToolContext, ToolMetadataKey, tool
from arcade_tdk.auth import Google

from arcade_google_docs.decorators import with_filepicker_fallback
from arcade_google_docs.utils import build_docs_service


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/get
# Example `arcade chat` query: `get document with ID 1234567890`
# Note: Document IDs are returned in the response of the Google Drive's `list_documents` tool
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/drive.file",
        ],
    ),
    requires_metadata=[ToolMetadataKey.CLIENT_ID, ToolMetadataKey.COORDINATOR_URL],
)
@with_filepicker_fallback
async def get_document_by_id(
    context: ToolContext,
    document_id: Annotated[str, "The ID of the document to retrieve."],
) -> Annotated[dict, "The document contents as a dictionary"]:
    """
    Get the latest version of the specified Google Docs document.
    """
    service = build_docs_service(context.get_auth_token_or_empty())

    # Execute the documents().get() method. Returns a Document object
    # https://developers.google.com/docs/api/reference/rest/v1/documents#Document
    request = service.documents().get(documentId=document_id)
    response = request.execute()
    return dict(response)
