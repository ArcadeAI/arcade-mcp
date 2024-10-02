import json
from typing import Annotated, Optional

from googleapiclient.errors import HttpError

from arcade.core.errors import ToolExecutionError
from arcade.core.schema import ToolContext
from arcade.sdk import tool
from arcade.sdk.auth import Google
from arcade_google.tools.utils import build_docs_service, remove_none_values


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/get
# Example arcade chat: get document 1234567890
# Note: Document IDs are returned in the response of the list_drive_files tool
# TODO: Ensure document_id is valid. If not, then get all document ids and raise Retryable Error with list of document ids
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
)
async def get_document(
    context: ToolContext,
    document_id: Annotated[str, "The ID of the document to retrieve"],
    suggestions_view_mode: Annotated[
        Optional[str], "The suggestions view mode to apply to the document"
    ] = None,
    include_tabs_content: Annotated[
        Optional[bool],
        "Whether to populate the Document.tabs field instead of the text content fields",
    ] = None,
) -> Annotated[str, "The document content as a JSON string"]:
    """
    Get the latest version of the specified document.
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

        return json.dumps(response)

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


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/create
@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/drive.file",
        ],
    )
)
async def create_blank_document(
    context: ToolContext, title: Annotated[str, "The title of the blank document to create"]
) -> Annotated[str, "The created document content as a JSON string"]:
    """
    Create a blank document with the specified title.
    """
    try:
        service = build_docs_service(context.authorization.token)

        body = {"title": title}

        # Execute the documents().create() method. Returns a Document object https://developers.google.com/docs/api/reference/rest/v1/documents#Document
        request = service.documents().create(body=body)
        response = request.execute()

        return json.dumps({
            "title": response["title"],
            "documentId": response["documentId"],
            "documentUrl": f"https://docs.google.com/document/d/{response['documentId']}/edit",
        })

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


# Uses https://developers.google.com/docs/api/reference/rest/v1/documents/batchUpdate
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
) -> Annotated[str, "The created document content as a JSON string"]:
    """
    Create a Google Docs document with the specified title and text content.
    """
    try:
        # First, create a blank document
        document = json.loads(await create_blank_document(context, title))

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

        return json.dumps({
            "title": document["title"],
            "documentId": document["documentId"],
            "documentUrl": f"https://docs.google.com/document/d/{document['documentId']}/edit",
        })

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
