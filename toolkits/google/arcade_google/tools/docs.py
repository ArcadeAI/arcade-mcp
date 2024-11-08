from typing import Annotated

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Google
from arcade_google.tools.utils import build_docs_service


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/get
# Example `arcade chat` query: `get document with ID 1234567890`
# Note: Document IDs are returned in the response of the Google Drive's `list_documents` tool
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/documents.readonly",
        ],
    )
)
async def get_document_by_id(
    context: ToolContext,
    document_id: Annotated[str, "The ID of the document to retrieve."],
) -> Annotated[dict, "The document contents as a dictionary"]:
    """
    Get the latest version of the specified Google Docs document.
    """
    service = build_docs_service(context.authorization.token)

    # Execute the documents().get() method. Returns a Document object
    # https://developers.google.com/docs/api/reference/rest/v1/documents#Document
    request = service.documents().get(documentId=document_id)
    response = request.execute()
    return response


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate
# Example `arcade chat` query: `insert "The END" at the end of document with ID 1234567890`
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/documents",
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

    service = build_docs_service(context.authorization.token)

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

    return response


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/create
# Example `arcade chat` query: `create blank document with title "My New Document"`
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/documents",
        ],
    )
)
async def create_blank_document(
    context: ToolContext, title: Annotated[str, "The title of the blank document to create"]
) -> Annotated[dict, "The created document's title, documentId, and documentUrl in a dictionary"]:
    """
    Create a blank Google Docs document with the specified title.
    """
    service = build_docs_service(context.authorization.token)

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
# Example `arcade chat` query: `create document with title "My New Document" and text content "Hello, World!"`
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/documents",
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

    service = build_docs_service(context.authorization.token)

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
