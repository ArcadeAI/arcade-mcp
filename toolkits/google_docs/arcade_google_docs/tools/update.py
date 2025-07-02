from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Google

from arcade_google_docs.tools.get import get_document_by_id
from arcade_google_docs.utils import build_docs_service


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate
# Example `arcade chat` query: `insert "The END" at the end of document with ID 1234567890`
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/drive.file",
        ],
    )
)
async def insert_text_at_end_of_document(
    context: ToolContext,
    document_id: Annotated[str, "The ID of the document to update."],
    text_content: Annotated[str, "The text content to insert into the document"],
) -> Annotated[dict, "The response from the batchUpdate API as a dict."]:
    """
    Updates an existing Google Docs document using the batchUpdate API endpoint.
    """
    document = await get_document_by_id(context, document_id)

    end_index = document["body"]["content"][-1]["endIndex"]

    service = build_docs_service(
        context.authorization.token if context.authorization and context.authorization.token else ""
    )

    requests = [
        {
            "insertText": {
                "location": {
                    "index": int(end_index) - 1,
                },
                "text": text_content,
            }
        }
    ]

    # Execute the documents().batchUpdate() method
    response = (
        service.documents()
        .batchUpdate(documentId=document_id, body={"requests": requests})
        .execute()
    )

    return dict(response)
