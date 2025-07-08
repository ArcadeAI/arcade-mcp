from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_notion_toolkit
from arcade_notion_toolkit.tools import (
    append_content_to_end_of_page,
    create_page,
    get_page_content_by_id,
    get_page_content_by_title,
)
from evals.constants import (
    GET_SMALL_PAGE_CONTENT_CONVERSATION,
    SMALL_PAGE_CONTENT,
    SMALL_PAGE_CONTENT_TO_APPEND,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_notion_toolkit)


@tool_eval()
def create_page_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools creating a Notion page"""
    suite = EvalSuite(
        name="Notion Create Page Evaluation",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Easy case
    suite.add_case(
        name="Create page easy difficulty",
        user_message=(
            "Create a page with the title '07/11/2027' and content '* drank a slurpie' "
            "under the parent page 'Daily Standup'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_page,
                args={
                    "parent_title": "Daily Standup",
                    "title": "07/11/2027",
                    "content": "* drank a slurpie",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="parent_title", weight=0.34),
            SimilarityCritic(critic_field="title", weight=0.33, similarity_threshold=0.95),
            SimilarityCritic(critic_field="content", weight=0.33, similarity_threshold=0.95),
        ],
    )

    # Medium case
    suite.add_case(
        name="Create page medium difficulty",
        user_message=(
            f"Create a page with the title 'Why Use Arcade?' and content {SMALL_PAGE_CONTENT}"
            "under the parent page 'Arcade Notes'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_page,
                args={
                    "parent_title": "Arcade Notes",
                    "title": "Why Use Arcade?",
                    "content": SMALL_PAGE_CONTENT,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="parent_title", weight=0.34),
            SimilarityCritic(critic_field="title", weight=0.33, similarity_threshold=0.95),
            SimilarityCritic(critic_field="content", weight=0.33, similarity_threshold=0.95),
        ],
    )

    # Hard case
    suite.add_case(
        name="Create page hard difficulty",
        user_message=(f"Add {SMALL_PAGE_CONTENT} as a subpage. Name it 'Why Use Arcade?'"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_page,
                args={
                    "parent_title": "Arcade Notes",
                    "title": "Why Use Arcade?",
                    "content": SMALL_PAGE_CONTENT,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="parent_title", weight=0.34),
            SimilarityCritic(critic_field="title", weight=0.33, similarity_threshold=0.95),
            SimilarityCritic(critic_field="content", weight=0.33, similarity_threshold=0.95),
        ],
        additional_messages=GET_SMALL_PAGE_CONTENT_CONVERSATION,
    )
    return suite


@tool_eval()
def get_page_content_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting the content of a Notion page"""
    suite = EvalSuite(
        name="Notion Get Page Content By ID Evaluation",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Easy case
    suite.add_case(
        name="Get page content by id easy difficulty",
        user_message="Get the content of the page with id 1b37a62b04d48079a902ce69ed7e7240",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_page_content_by_id,
                args={
                    "page_id": "1b37a62b04d48079a902ce69ed7e7240",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="page_id", weight=1),
        ],
    )

    # Medium case
    suite.add_case(
        name="Get page content medium difficulty",
        user_message=(
            "Summarize the main points in 1b37a62b04d48079a902ce69ed7e7240. "
            "Also, does 'Tool Calling with Arcade' actually talk about tools?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_page_content_by_id,
                args={
                    "page_id": "1b37a62b04d48079a902ce69ed7e7240",
                },
            ),
            ExpectedToolCall(
                func=get_page_content_by_title,
                args={
                    "title": "Tool Calling with Arcade",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="page_id", weight=0.5),
            BinaryCritic(critic_field="title", weight=0.5),
        ],
    )

    # Hard case
    suite.add_case(
        name="Get page content hard difficulty",
        user_message=(
            "Compare it's main points against 'Tool Calling with Arcade' and "
            "'Tool Execution with Arcade'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_page_content_by_title,
                args={
                    "title": "Tool Calling with Arcade",
                },
            ),
            ExpectedToolCall(
                func=get_page_content_by_title,
                args={
                    "title": "Tool Execution with Arcade",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="title", weight=1),
        ],
        additional_messages=GET_SMALL_PAGE_CONTENT_CONVERSATION,
    )

    return suite


@tool_eval()
def append_page_content_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools appending content to an existing Notion page"""
    suite = EvalSuite(
        name="Notion Append Content To End Of Page",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Append page content",
        user_message=f"Add this to the end of that page:\n{SMALL_PAGE_CONTENT_TO_APPEND}",
        expected_tool_calls=[
            ExpectedToolCall(
                func=append_content_to_end_of_page,
                args={
                    "page_id_or_title": "Arcade Notes",
                    "content": SMALL_PAGE_CONTENT_TO_APPEND,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="page_id_or_title", weight=0.5),
            SimilarityCritic(critic_field="content", weight=0.5, similarity_threshold=0.95),
        ],
        additional_messages=GET_SMALL_PAGE_CONTENT_CONVERSATION,
    )
    return suite
