from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google
from arcade_google.tools import (
    create_blank_document,
    create_document_from_text,
    get_document_by_id,
    insert_text_at_end_of_document,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)


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
