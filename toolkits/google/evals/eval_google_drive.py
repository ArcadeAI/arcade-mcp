from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import arcade_google
from arcade_google.tools.drive import list_documents
from arcade_google.tools.models import Corpora, OrderBy

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google)


@tool_eval()
def drive_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Drive tools."""
    suite = EvalSuite(
        name="Google Drive Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Drive documents using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List documents in Google Drive",
        user_message="show me the titles of my 39 most recently created documents. Show me the newest ones first and the oldest ones last.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_documents,
                args={
                    "corpora": Corpora.USER,
                    "order_by": OrderBy.CREATED_TIME_DESC,
                    "supports_all_drives": False,
                    "limit": 39,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="corpora", weight=0.25),
            BinaryCritic(critic_field="order_by", weight=0.25),
            BinaryCritic(critic_field="supports_all_drives", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.25),
        ],
    )

    suite.add_case(
        name="List documents in Google Drive based on title keywords",
        user_message="list all documents that have title that contains the word'greedy' and also the phrase 'Joe's algo'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_documents,
                args={
                    "corpora": Corpora.USER,
                    "title_keywords": ["greedy", "Joe's algo"],
                    "order_by": OrderBy.MODIFIED_TIME_DESC,
                    "supports_all_drives": False,
                    "limit": 50,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="order_by", weight=0.25),
            BinaryCritic(critic_field="title_keywords", weight=0.75),
        ],
    )

    suite.add_case(
        name="List documents in shared drives",
        user_message="List the 5 documents from all drives that nobody has touched in forever, including shared ones.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_documents,
                args={
                    "corpora": Corpora.ALL_DRIVES,
                    "order_by": OrderBy.MODIFIED_TIME,
                    "supports_all_drives": True,
                    "limit": 5,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="corpora", weight=0.25),
            BinaryCritic(critic_field="order_by", weight=0.25),
            BinaryCritic(critic_field="supports_all_drives", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.25),
        ],
    )

    suite.add_case(
        name="No tool call case",
        user_message="List my 10 most recently modified documents that are stored in my Microsoft OneDrive.",
        expected_tool_calls=[],
        critics=[],
    )

    return suite
