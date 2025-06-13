from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google
from arcade_google.models import DocumentFormat, OrderBy
from arcade_google.tools import (
    get_file_tree_structure,
    search_and_retrieve_documents,
    search_documents,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)


@tool_eval()
def get_file_tree_structure_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Drive tools."""
    suite = EvalSuite(
        name="Google Drive Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Drive documents using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="get my google drive's file tree structure including shared drives",
        user_message="get my google drive's file tree structure including shared drives",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": True,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
    )

    suite.add_case(
        name="get my google drive's file tree structure without shared drives",
        user_message="get my google drive's file tree structure without shared drives",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": False,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
    )

    suite.add_case(
        name="what are the files in the folder 'hello world' in my google drive?",
        user_message="what are the files in the folder 'hello world' in my google drive?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": False,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
    )

    suite.add_case(
        name="how many files are there in all my google drives, including shared ones?",
        user_message="how many files are there in all my google drives, including shared ones?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": True,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
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
