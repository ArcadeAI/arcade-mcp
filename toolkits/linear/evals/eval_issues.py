"""
Evaluation suite for Linear get_issue tool.
"""

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_linear
from arcade_linear.tools.issues import get_issue

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

# Tool catalog
catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def get_issue_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for get_issue tool"""
    suite = EvalSuite(
        name="Get Issue Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user get detailed information about Linear issues."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get complete issue details",
        user_message="Show me complete details for issue API-789",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue,
                args={
                    "issue_id": "API-789",
                    "include_comments": True,
                    "include_attachments": True,
                    "include_relations": True,
                    "include_children": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.6),
            BinaryCritic(critic_field="include_comments", weight=0.1),
            BinaryCritic(critic_field="include_attachments", weight=0.1),
            BinaryCritic(critic_field="include_relations", weight=0.1),
            BinaryCritic(critic_field="include_children", weight=0.1),
        ],
    )

    suite.add_case(
        name="Get issue dependencies",
        user_message="Find all dependencies for issue PROJ-100",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue,
                args={
                    "issue_id": "PROJ-100",
                    "include_relations": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.7),
            BinaryCritic(critic_field="include_relations", weight=0.3),
        ],
    )

    suite.add_case(
        name="Get issue with sub-issues and dependencies",
        user_message="Get issue FE-123 with all related sub-issues and dependencies",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue,
                args={
                    "issue_id": "FE-123",
                    "include_relations": True,
                    "include_children": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            BinaryCritic(critic_field="include_relations", weight=0.25),
            BinaryCritic(critic_field="include_children", weight=0.25),
        ],
    )

    return suite
