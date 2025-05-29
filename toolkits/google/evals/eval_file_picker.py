from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google
from arcade_google.tools import generate_google_file_picker_url

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_google)

history_1 = [
    {
        "role": "user",
        "content": "get the contents of my spreadsheet named 'How to teach an old dog a new trick'",
    },
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_errutwjcpZLiHu8LKip6XKLq",
                "type": "function",
                "function": {
                    "name": "Google_SearchDocuments",
                    "arguments": '{"document_contains":["How to teach an old dog a new trick"],"limit":5}',
                },
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"documents":[],"documents_count":0}',
        "tool_call_id": "call_errutwjcpZLiHu8LKip6XKLq",
        "name": "Google_SearchDocuments",
    },
    {
        "role": "assistant",
        "content": "It seems that I don't have access to your spreadsheet named \"How to teach an old dog a new trick.\" If you need help retrieving the data, you can check your cloud storage or computer files where the spreadsheet might be saved, such as Google Sheets, Microsoft Excel, or other spreadsheet software. Let me know if there's anything specific you'd like assistance with regarding the content!",
    },
]

history_2 = [
    {"role": "system", "content": "Today is 2025-04-15, Tuesday."},
    {
        "role": "user",
        "content": "I got this error from you: \n❌ Arcade Chat failed with error: Error code: 500 - {'name':'non_retryable_tool_call_error', 'message': 'tool call failed - \nGoogle.InsertTextAtEndOfDocument failed: Error inexecution of GetDocumentById: Error in get_document_by_id: <HttpError 404 when\nrequestinghttps://docs.googleapis.com/v1/documents/192394932924?alt=json returned \"Requested entity was not found.\". Details: \n\"Requestedentity was not found.\">'}",
    },
    {
        "role": "assistant",
        "content": "The error message indicates that there was an attempt to retrieve a document with a specific ID \\(`192394932924`) from Google Docs, but the document could not be found. The HTTP 404 error code means that the document doesn't \\exist or is not accessible with the current permissions. Here's what you can do:\n\n1. **Check Document ID:** Make sure the \\document ID (`192394932924`) is correct. A typo or incorrect ID will lead to this error.\n\n2. **Permissions:** Ensure that you \\have permission to access the document. If the document is owned by someone else or is in a shared drive with restricted access,\\you might not be able to view it.\n\n3. **Document Existence:** Double-check that the document hasn't been deleted or moved to \the trash or a location you don't have access to.\n\nLet me know if there's anything else you'd like to address or any other \assistance you need!",
    },
]


@tool_eval()
def file_picker_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Gmail tools."""
    suite = EvalSuite(
        name="File Picker Tools Evaluation",
        system_message="You are an AI assistant that can perform actions for the user using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get file picker url 1",
        user_message="I am certain that the spreadsheet exists",
        expected_tool_calls=[
            ExpectedToolCall(
                func=generate_google_file_picker_url,
                args={},
            )
        ],
        additional_messages=history_1,
    )

    suite.add_case(
        name="Get file picker url 2",
        user_message="Please help in anyway you can. I'm literally looking at the document right now in the browser.",
        expected_tool_calls=[
            ExpectedToolCall(func=generate_google_file_picker_url, args={}),
        ],
        additional_messages=history_2,
    )

    suite.add_case(
        name="Get file picker url 3",
        user_message="I want to give you permissions to more files in my Drive right now.",
        expected_tool_calls=[
            ExpectedToolCall(func=generate_google_file_picker_url, args={}),
        ],
    )

    return suite
