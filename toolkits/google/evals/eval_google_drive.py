from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import arcade_google
from arcade_google.models import Corpora, DocumentFormat, OrderBy
from arcade_google.tools.drive import list_documents, search_and_retrieve_documents

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)


@tool_eval()
def list_documents_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Drive tools."""
    suite = EvalSuite(
        name="Google Drive Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Drive documents using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List documents in Google Drive",
        user_message="show me the titles of my 39 most recently created documents. Show me the ones created most recently first.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_documents,
                args={
                    "order_by": [OrderBy.CREATED_TIME_DESC.value],
                    "limit": 39,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="order_by", weight=0.5),
            BinaryCritic(critic_field="limit", weight=0.5),
        ],
    )

    suite.add_case(
        name="List documents in Google Drive based on document keywords",
        user_message="list the documents that contain the word 'greedy' and the phrase 'hello, world'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_documents,
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
        name="List documents in shared drives",
        user_message="List the 5 documents from all drives corpora that nobody has touched in forever, including shared ones.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_documents,
                args={
                    "corpora": Corpora.ALL_DRIVES.value,
                    "supports_all_drives": True,
                    "limit": 5,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="corpora", weight=1 / 3),
            BinaryCritic(critic_field="supports_all_drives", weight=1 / 3),
            BinaryCritic(critic_field="limit", weight=1 / 3),
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
        user_message="write a summary of the documents in my Google Drive about 'MX Engineering'",
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
        user_message="Get documents that mention 'Q1 report' but do not include the expression 'Project XYZ'.",
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
