from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import arcade_google
from arcade_google.models import Corpora, OrderBy
from arcade_google.tools.drive import list_documents

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
        name="List documents in Google Drive based on title keywords",
        user_message="list all documents that have title that contains the word'greedy' and also the phrase 'Joe's algo'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_documents,
                args={
                    "title_keywords": ["greedy", "Joe's algo"],
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="title_keywords", weight=1.0),
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


# @tool_eval()
# def search_and_retrieve_documents_eval_suite() -> EvalSuite:
#     """Create an evaluation suite for Google Drive search and retrieve tools."""
#     suite = EvalSuite(
#         name="Google Drive Tools Evaluation",
#         system_message="You are an AI assistant that can manage Google Drive documents using the provided tools.",
#         catalog=catalog,
#         rubric=rubric,
#     )

#     suite.add_case(
#         name="Search and retrieve documents in Google Drive",
#         user_message="write a summary of the documents in my Google Drive about 'MX Engineering'",
#         expected_tool_calls=[
#             ExpectedToolCall(
#                 func=search_and_retrieve_documents_in_markdown,
#                 args={
#                     "content_contains": ["The Birth of Machine Experience Engineering"],
#                 },
#             )
#         ],
#         critics=[
#             BinaryCritic(critic_field="content_contains", weight=1.0),
#         ],
#     )

#     return suite
