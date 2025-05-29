from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_confluence
from arcade_confluence.enums import PageUpdateMode
from arcade_confluence.tools import (
    create_page,
    get_page,
    get_pages_by_id,
    rename_page,
    update_page_content,
)
from evals.conversations import create_page_1, get_space_hierarchy_1
from evals.critics import ListCritic

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_confluence)


@tool_eval()
def confluence_get_page_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence get_page tool evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get page by ID",
        user_message="Get page 65816",
        expected_tool_calls=[ExpectedToolCall(func=get_page, args={"page_identifier": 65816})],
        rubric=rubric,
        critics=[BinaryCritic(critic_field="page_identifier", weight=1)],
    )

    suite.add_case(
        name="Get page by title",
        user_message="Get my 'Poem - May 24th' page",
        expected_tool_calls=[
            ExpectedToolCall(func=get_page, args={"page_identifier": "Poem - May 24th"})
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="page_identifier", weight=1),
        ],
    )

    suite.add_case(
        name="Get page based on previous conversation",
        user_message=(
            "Get the content of my daily note. You MUST use the page's title when getting the page."
        ),
        expected_tool_calls=[ExpectedToolCall(func=get_page, args={"page_identifier": "10-03-98"})],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="page_identifier", weight=1),
        ],
        additional_messages=get_space_hierarchy_1,
    )

    return suite


@tool_eval()
def confluence_get_multiple_pages_by_id_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence get_multiple_pages_by_id tool evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get multiple pages by ID",
        user_message="Get 98418, 4685837, 5242883, 5275653, 5242903, 5242913 pages",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_pages_by_id,
                args={"page_ids": ["98418", "4685837", "5242883", "5275653", "5242903", "5242913"]},
            )
        ],
        rubric=rubric,
        critics=[
            ListCritic(critic_field="page_ids", order_matters=False, weight=1),
        ],
    )

    suite.add_case(
        name="Get multiple pages by ID with existing conversation",
        user_message=("Get the content of all pages in the space except 4685837"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_pages_by_id,
                args={"page_ids": ["98418", "5242883", "5275653", "5242903", "5242913"]},
            )
        ],
        rubric=rubric,
        critics=[
            ListCritic(critic_field="page_ids", order_matters=False, weight=1),
        ],
        additional_messages=get_space_hierarchy_1,
    )

    return suite


@tool_eval()
def confluence_create_page_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence create_page tool evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create a page",
        user_message=(
            "Make a page within the softwareeng space called 'TODOs' under the 4830960 folder. "
            "Within it, make a list of all the TODOs for the day which are "
            "1. Write a blog post about the future of AI"
            "2. Write an agent that calls my mom at 5:30 every Friday evening"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_page,
                args={
                    "space_identifier": "softwareeng",
                    "title": "TODOs",
                    "content": "1. Write a blog post about the future of AI\n2. Write an agent that calls my mom at 5:30 every Friday evening",  # noqa: E501
                    "parent_id": "4830960",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="space_identifier", weight=1 / 4),
            BinaryCritic(critic_field="title", weight=1 / 4),
            SimilarityCritic(critic_field="content", weight=1 / 4),
            BinaryCritic(critic_field="parent_id", weight=1 / 4),
        ],
    )

    return suite


@tool_eval()
def confluence_update_page_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence update page tools evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Update page content",
        user_message="Thanks, now append '3. Walk the dog' to the end of the list",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_page_content,
                args={
                    "page_identifier": "5439489",
                    "content": "3. Walk the dog",
                    "update_mode": PageUpdateMode.APPEND,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="page_identifier", weight=1 / 3),
            SimilarityCritic(critic_field="content", weight=1 / 3),
            BinaryCritic(critic_field="update_mode", weight=1 / 3),
        ],
        additional_messages=create_page_1,
    )

    suite.extend_case(
        name="Rename page",
        user_message="Actually, rename it to 'My TODOs'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=rename_page,
                args={"page_identifier": "5439489", "title": "My TODOs"},
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="page_identifier", weight=1 / 2),
            BinaryCritic(critic_field="title", weight=1 / 2),
        ],
    )
    return suite
