import json
from typing import Annotated, Optional

from googleapiclient.errors import HttpError

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google
from arcade_google.tools.utils import build_docs_service, remove_none_values


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/get
# Example `arcade chat` query: `get document with ID 1234567890`
# Note: Document IDs are returned in the response of the Google Drive's `list_documents` tool
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
)
async def get_document(
    context: ToolContext,
    document_id: Annotated[str, "The ID of the document to retrieve."],
    suggestions_view_mode: Annotated[
        Optional[str], "The suggestions view mode to apply to the document"
    ] = None,
    include_tabs_content: Annotated[
        Optional[bool],
        "Whether to populate the Document.tabs field instead of the text content fields",
    ] = None,
) -> Annotated[dict, "The document contents as a dictionary"]:
    """
    Get the latest version of the specified Google Docs document.
    """
    try:
        service = build_docs_service(context.authorization.token)

        params = {
            "suggestionsViewMode": suggestions_view_mode,
            "includeTabsContent": include_tabs_content,
        }
        params = remove_none_values(params)

        # Execute the documents().get() method. Returns a Document object https://developers.google.com/docs/api/reference/rest/v1/documents#Document
        request = service.documents().get(documentId=document_id, **params)
        response = request.execute()

    except HttpError as e:
        raise ToolExecutionError(
            f"HttpError during execution of '{get_document.__name__}' tool.",
            str(e),
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Unexpected Error encountered during execution of '{get_document.__name__}' tool.",
            str(e),
        )
    else:
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
    try:
        document = json.loads(await get_document(context, document_id))

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

    except HttpError as e:
        raise ToolExecutionError(
            f"HttpError during execution of '{insert_text_at_end_of_document.__name__}' tool.",
            str(e),
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Unexpected Error encountered during execution of '{insert_text_at_end_of_document.__name__}' tool.",
            str(e),
        )
    else:
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
    try:
        service = build_docs_service(context.authorization.token)

        body = {"title": title}

        # Execute the documents().create() method. Returns a Document object https://developers.google.com/docs/api/reference/rest/v1/documents#Document
        request = service.documents().create(body=body)
        response = request.execute()

    except HttpError as e:
        raise ToolExecutionError(
            f"HttpError during execution of '{create_blank_document.__name__}' tool.",
            str(e),
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Unexpected Error encountered during execution of '{create_blank_document.__name__}' tool.",
            str(e),
        )
    else:
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
    try:
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

    except HttpError as e:
        raise ToolExecutionError(
            f"HttpError during execution of '{create_document_from_text.__name__}' tool.",
            str(e),
        )
    except Exception as e:
        raise ToolExecutionError(
            f"Unexpected Error encountered during execution of '{create_document_from_text.__name__}' tool.",
            str(e),
        )
    else:
        return {
            "title": document["title"],
            "documentId": document["documentId"],
            "documentUrl": f"https://docs.google.com/document/d/{document['documentId']}/edit",
        }
