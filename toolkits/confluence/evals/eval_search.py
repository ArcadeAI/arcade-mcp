from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade.sdk.eval.critic import BinaryCritic

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
        expected_tool_calls=[ExpectedToolCall(func=search_content, args={"terms": ["Arcade.dev"]})],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="terms", weight=1),
        ],
    )

    suite.add_case(
        name="Search for content - medium case",
        user_message=(
            "Find 20 pages that contain 'Arcade' or 'AI', or that talk about 'tool calls'"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_content,
                args={
                    "terms": ["Arcade", "AI"],
                    "phrases": ["tool calls"],
                    "limit": 20,
                },
            )
        ],
        rubric=rubric,
        critics=[
            ListCritic(critic_field="terms", weight=0.45, case_sensitive=False),
            ListCritic(critic_field="phrases", weight=0.45, case_sensitive=False),
            BinaryCritic(critic_field="limit", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for content - hard case",
        user_message=(
            "Look for 25 databases with titles that start with 'How to', "
            "and also have 'carborator' in the content"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_content,
                args={
                    "terms": ["carborator"],
                    "phrases": ["How to"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            ListCritic(critic_field="terms", weight=0.5, case_sensitive=False),
            ListCritic(critic_field="phrases", weight=0.5, case_sensitive=False),
        ],
    )

    return suite
