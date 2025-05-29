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
    search_content,
)
from evals.critics import ListCritic

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_confluence)


@tool_eval()
def confluence_search_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Confluence search content tool evaluation",
        system_message="You are an AI assistant with access to Confluence tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search for content - easy case",
        user_message="Find all pages that contain 'Arcade.dev'",
        expected_tool_calls=[
            ExpectedToolCall(func=search_content, args={"can_contain_any": ["Arcade.dev"]})
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="can_contain_any", weight=1),
        ],
    )

    suite.add_case(
        name="Search for content - medium case",
        user_message=("Find 20 pages that contain 'Arcade' or 'AI', or 'tool calls'"),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_content,
                args={
                    "can_contain_any": ["Arcade", "AI", "tool calls"],
                    "limit": 20,
                },
            )
        ],
        rubric=rubric,
        critics=[
            ListCritic(
                critic_field="can_contain_any",
                weight=0.9,
                case_sensitive=False,
                order_matters=False,
            ),
            BinaryCritic(critic_field="limit", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for content - hard case",
        user_message=(
            "Look for 25 databases that have 'How to', "
            "and also have 'carborator' in the content and "
            "also has one of the following: 'money', 'redbull gives you wings', "
            "'honey hole', 'don't snap the pasta!'."
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_content,
                args={
                    "must_contain_all": ["carborator", "How to"],
                    "can_contain_any": [
                        "money",
                        "redbull gives you wings",
                        "honey hole",
                        "don't snap the pasta!",
                    ],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            ListCritic(
                critic_field="must_contain_all",
                weight=0.5,
                case_sensitive=False,
                order_matters=False,
            ),
            ListCritic(
                critic_field="can_contain_any",
                weight=0.5,
                case_sensitive=False,
                order_matters=False,
            ),
        ],
    )

    return suite
