from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_confluence
from arcade_confluence.tools import (
    get_space,
    get_space_hierarchy,
    list_spaces,
)
from evals.conversations import list_spaces_1

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_confluence)


@tool_eval()
def confluence_get_space_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence get_space tool evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get two spaces - one by ID, and one by key",
        user_message="Get spaces 3498573 and 'Poetry'",
        expected_tool_calls=[
            ExpectedToolCall(func=get_space, args={"space_identifier": 3498573}),
            ExpectedToolCall(func=get_space, args={"space_identifier": "Poetry"}),
        ],
        rubric=rubric,
        critics=[BinaryCritic(critic_field="space_identifier", weight=1)],
    )

    return suite


@tool_eval()
def confluence_list_spaces_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence list_spaces tool evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List the next space using a pagination token",
        user_message="get the next one",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_spaces,
                args={
                    "limit": 1,
                    "pagination_token": "eyJpZCI6MjMyNjc5NCwic3BhY2VTb3J0T3JkZXIiOnsiZmllbGQiOiJOQU1FIiwiZGlyZWN0aW9uIjoiQVNDRU5ESU5HIn0sInNwYWNlU29ydE9yZGVyVmFsdWUiOiJlcmljYXJjYWRlIn0=",  # noqa: E501
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="limit", weight=0.3),
            BinaryCritic(critic_field="pagination_token", weight=0.7),
        ],
        additional_messages=list_spaces_1,
    )

    return suite


@tool_eval()
def confluence_get_space_hierarchy_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence get_space_hierarchy tool evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get the hierarchy of a space",
        user_message=(
            "What is the best file location within my 'Poetry' space to create a new page "
            "named 'Rough Draft - Poem for King Henry VIII'?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_space_hierarchy,
                args={
                    "space_identifier": "Poetry",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="space_identifier", weight=1),
        ],
    )

    return suite
