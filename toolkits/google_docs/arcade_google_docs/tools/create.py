from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Google

from arcade_google_docs.utils import build_docs_service


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/create
# Example `arcade chat` query: `create blank document with title "My New Document"`
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/drive.file",
        ],
    )
)
async def create_blank_document(
    context: ToolContext, title: Annotated[str, "The title of the blank document to create"]
) -> Annotated[dict, "The created document's title, documentId, and documentUrl in a dictionary"]:
    """
    Create a blank Google Docs document with the specified title.
    """
    service = build_docs_service(context.get_auth_token_or_empty())

    body = {"title": title}

    # Execute the documents().create() method. Returns a Document object https://developers.google.com/docs/api/reference/rest/v1/documents#Document
    request = service.documents().create(body=body)
    response = request.execute()

    return {
        "title": response["title"],
        "documentId": response["documentId"],
        "documentUrl": f"https://docs.google.com/document/d/{response['documentId']}/edit",
    }


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate
# Example `arcade chat` query:
#   `create document with title "My New Document" and text content "Hello, World!"`
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/drive.file",
        ],
    )
)
async def create_document_from_text(
    context: ToolContext,
    title: Annotated[str, "The title of the document to create"],
    text_content: Annotated[str, "The text content to insert into the document"],
) -> Annotated[dict, "The created document's title, documentId, and documentUrl in a dictionary"]:
    """
    Create a Google Docs document with the specified title and text content.
    """
    # First, create a blank document
    document = await create_blank_document(context, title)

    service = build_docs_service(context.get_auth_token_or_empty())

    requests = [
        {
            "insertText": {
                "location": {
                    "index": 1,
                },
                "text": text_content,
            }
        }
    ]

    # Execute the batchUpdate method to insert text
    service.documents().batchUpdate(
        documentId=document["documentId"], body={"requests": requests}
    ).execute()

    return {
        "title": document["title"],
        "documentId": document["documentId"],
        "documentUrl": f"https://docs.google.com/document/d/{document['documentId']}/edit",
    }
