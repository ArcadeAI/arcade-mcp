from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google_docs
from arcade_google_docs.enum import DocumentFormat, OrderBy
from arcade_google_docs.tools import (
    create_blank_document,
    create_document_from_text,
    get_document_by_id,
    insert_text_at_end_of_document,
    search_and_retrieve_documents,
    search_documents,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google_docs)


@tool_eval()
def docs_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Docs tools."""
    suite = EvalSuite(
        name="Google Docs Tools Evaluation",
        system_message="You are an AI assistant that can create and manage Google Docs using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # A previous tool call to list_documents
    additional_messages = [
        {"role": "user", "content": "list my 10 most recently created docs"},
        {
            "role": "assistant",
            "content": "Please go to this URL and authorize the action: [Link](https://accounts.google.com/)",
        },
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_gegK723W2hXsORjBmq1Oexqk",
                    "type": "function",
                    "function": {
                        "name": "Google_ListDocuments",
                        "arguments": '{"limit":10,"order_by":"createdTime desc"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "content": '{"documents":[{"id":"1e0rCoT1Yd14WuuEvd3hSUcN_-VD3df4T3Q08uLm3TWc","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst10"},{"id":"1eTSWd-5zQds8K9OWYygwtCFMUyuuMize3bh3HaRsKts","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst9"},{"id":"19Dqugn0rVi89K0C__lpg1HbhQOTenccyZOhPgivTHMs","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst8"},{"id":"1RCibzx14eqP3vS9yI4nD13OKf8Vee56RiszS53OkR7I","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst7"},{"id":"1imFb04JQuBn8SiSsRFf6fEuYCyXkbII4KX8fsmnT0jo","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst6"},{"id":"1ZC3oypdfLWFgBd-emeSykJf9tZOae6USsFboygRCr-w","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst5"},{"id":"1-gFGNWmwLxEiKa6NNixLNq3X-phXRMORVZfVTfBg8Sc","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst4"},{"id":"1eQ8UBO_PY3Lem4R8OVdIc9ODXt0MrSUAnEu994Qz8P8","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst3"},{"id":"1TOxB0MLry-JzntDWDT1LFywTLdr3XDWPT5L5UsHMs5c","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst2"},{"id":"1a1UQ7C90s8kGfnO8k6wfAZz_Cy5nGN2MkCoRB5y2j3w","kind":"drive#file","mimeType":"application/vnd.google-apps.document","name":"Tst1"}],"documents_count":10}',
            "tool_call_id": "call_gegK723W2hXsORjBmq1Oexqk",
            "name": "Google_ListDocuments",
        },
        {
            "role": "assistant",
            "content": "Here are your 10 most recently created Google Docs:\n\n1. [Tst10](https://docs.google.com/document/d/1e0rCoT1Yd14WuuEvd3hSUcN_-VD3df4T3Q08uLm3TWc)\n2. [Tst9](https://docs.google.com/document/d/1eTSWd-5zQds8K9OWYygwtCFMUyuuMize3bh3HaRsKts)\n3. [Tst8](https://docs.google.com/document/d/19Dqugn0rVi89K0C__lpg1HbhQOTenccyZOhPgivTHMs)\n4. [Tst7](https://docs.google.com/document/d/1RCibzx14eqP3vS9yI4nD13OKf8Vee56RiszS53OkR7I)\n5. [Tst6](https://docs.google.com/document/d/1imFb04JQuBn8SiSsRFf6fEuYCyXkbII4KX8fsmnT0jo)\n6. [Tst5](https://docs.google.com/document/d/1ZC3oypdfLWFgBd-emeSykJf9tZOae6USsFboygRCr-w)\n7. [Tst4](https://docs.google.com/document/d/1-gFGNWmwLxEiKa6NNixLNq3X-phXRMORVZfVTfBg8Sc)\n8. [Tst3](https://docs.google.com/document/d/1eQ8UBO_PY3Lem4R8OVdIc9ODXt0MrSUAnEu994Qz8P8)\n9. [Tst2](https://docs.google.com/document/d/1TOxB0MLry-JzntDWDT1LFywTLdr3XDWPT5L5UsHMs5c)\n10. [Tst1](https://docs.google.com/document/d/1a1UQ7C90s8kGfnO8k6wfAZz_Cy5nGN2MkCoRB5y2j3w)\n\nYou can click the links to open each document.",
        },
    ]

    suite.add_case(
        name="Get document content",
        user_message="Can you read me the contents of Tst9 doc and also Tst10 doc please",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_document_by_id,
                args={
                    "document_id": "1eTSWd-5zQds8K9OWYygwtCFMUyuuMize3bh3HaRsKts",
                },
            ),
            ExpectedToolCall(
                func=get_document_by_id,
                args={
                    "document_id": "1e0rCoT1Yd14WuuEvd3hSUcN_-VD3df4T3Q08uLm3TWc",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="document_id", weight=0.6),
        ],
        additional_messages=additional_messages,
    )

    suite.add_case(
        name="Insert text at end of document",
        user_message="Please add the text 'This is a new paragraph.' to the end of Tst4.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=insert_text_at_end_of_document,
                args={
                    "document_id": "1-gFGNWmwLxEiKa6NNixLNq3X-phXRMORVZfVTfBg8Sc",
                    "text_content": "This is a new paragraph.",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="document_id", weight=0.5),
            SimilarityCritic(critic_field="text_content", weight=0.5),
        ],
        additional_messages=additional_messages,
    )

    suite.add_case(
        name="Read the contents of two documents and then insert text at end of a different document.",
        user_message="Can you read me the contents of Tst9 doc and also Tst10 doc please. Also, please add the text 'This is a new paragraph.' to the end of Tst4.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=insert_text_at_end_of_document,
                args={
                    "document_id": "1-gFGNWmwLxEiKa6NNixLNq3X-phXRMORVZfVTfBg8Sc",
                    "text_content": "This is a new paragraph.",
                },
            ),
            ExpectedToolCall(
                func=get_document_by_id,
                args={
                    "document_id": "1eTSWd-5zQds8K9OWYygwtCFMUyuuMize3bh3HaRsKts",
                },
            ),
            ExpectedToolCall(
                func=get_document_by_id,
                args={
                    "document_id": "1e0rCoT1Yd14WuuEvd3hSUcN_-VD3df4T3Q08uLm3TWc",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="document_id", weight=0.3),
            SimilarityCritic(critic_field="text_content", weight=0.3),
        ],
        additional_messages=additional_messages,
    )

    suite.add_case(
        name="Create blank document",
        user_message="Create a new Doc titled 'Meeting Notes'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_blank_document,
                args={
                    "title": "Meeting Notes",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="title", weight=1.0),
        ],
    )

    suite.add_case(
        name="Create document from text",
        user_message="Create a new doc called To-Do List with the content 'Buy groceries, Call mom, Finish report'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_document_from_text,
                args={
                    "title": "To-Do List",
                    "text_content": "Buy groceries\nCall mom\nFinish report",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="title", weight=0.5),
            SimilarityCritic(critic_field="text_content", weight=0.5),
        ],
    )

    suite.add_case(
        name="No tool call case",
        user_message="Create a new microsoft word document titled 'My Resume'.",
        expected_tool_calls=[],
        critics=[],
    )

    return suite


@tool_eval()
def search_documents_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Drive tools."""
    suite = EvalSuite(
        name="Google Drive Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Drive documents using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search documents in Google Drive",
        user_message="get my 49 most recently created documents, list the ones created most recently first.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_documents,
                args={
                    "order_by": [OrderBy.CREATED_TIME_DESC.value],
                    "limit": 49,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="order_by", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search documents in Google Drive based on document keywords",
        user_message="Search the documents that contain the word 'greedy' and the phrase 'hello, world'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_documents,
                args={
                    "document_contains": ["greedy", "hello, world"],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="document_contains", weight=1.0),
        ],
    )

    suite.add_case(
        name="Search documents in a specific Google Drive based on document keywords",
        user_message="Search the documents that contain the word 'greedy' and the phrase 'hello, world' in the drive with id 'abc123'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_documents,
                args={
                    "document_contains": ["greedy", "hello, world"],
                    "search_only_in_shared_drive_id": "abc123",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="search_only_in_shared_drive_id", weight=0.5),
            BinaryCritic(critic_field="document_contains", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search documents in a Google Drive Workspace organization domain based on document keywords",
        user_message="Search the documents that contain the phrase 'hello, world' in the organization domain",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_documents,
                args={
                    "document_contains": ["hello, world"],
                    "include_organization_domain_documents": True,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5),
            BinaryCritic(critic_field="document_contains", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search documents in shared drives",
        user_message="Search the 5 documents from all drives corpora that nobody has touched in forever, excluding shared drives.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_documents,
                args={
                    "limit": 5,
                    "include_shared_drives": False,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
    )

    suite.add_case(
        name="No tool call case",
        user_message="List my 10 most recently modified documents that are stored in my Microsoft OneDrive.",
        expected_tool_calls=[],
        critics=[],
    )

    return suite


@tool_eval()
def search_and_retrieve_documents_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Drive search and retrieve tools."""
    suite = EvalSuite(
        name="Google Drive Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Drive documents using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search and retrieve (write summary)",
        user_message="Write a summary of the documents in my Google Drive about 'MX Engineering'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_and_retrieve_documents,
                args={
                    "document_contains": ["MX Engineering"],
                    "return_format": DocumentFormat.MARKDOWN,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="document_contains", weight=0.5),
            BinaryCritic(critic_field="return_format", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search and retrieve (project proposal)",
        user_message="Display the document contents in HTML format from my Google Drive that contain the phrase 'project proposal'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_and_retrieve_documents,
                args={
                    "document_contains": ["project proposal"],
                    "return_format": DocumentFormat.HTML,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="document_contains", weight=0.5),
            BinaryCritic(critic_field="return_format", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search and retrieve (meeting notes)",
        user_message="Retrieve documents that contain both 'meeting notes' and 'budget' in JSON format.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_and_retrieve_documents,
                args={
                    "document_contains": ["meeting notes", "budget"],
                    "return_format": DocumentFormat.GOOGLE_API_JSON,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="document_contains", weight=0.5),
            BinaryCritic(critic_field="return_format", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search and retrieve (Q1 report)",
        user_message="Show me the content of the documents that mention 'Q1 report' but do not include the expression 'Project XYZ'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_and_retrieve_documents,
                args={
                    "document_contains": ["Q1 report"],
                    "document_not_contains": ["Project XYZ"],
                    "return_format": DocumentFormat.MARKDOWN,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="document_contains", weight=1 / 3),
            BinaryCritic(critic_field="document_not_contains", weight=1 / 3),
            BinaryCritic(critic_field="return_format", weight=1 / 3),
        ],
    )

    return suite
