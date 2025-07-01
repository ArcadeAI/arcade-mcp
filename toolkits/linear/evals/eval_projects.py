"""
Comprehensive evaluation suite for Linear project management tools.
"""

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_linear
from arcade_linear.tools.issues import search_issues
from arcade_linear.tools.projects import get_projects

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def projects_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for project management tools"""
    suite = EvalSuite(
        name="Projects Management Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user manage Linear projects and project-related issues."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Show me all projects in the workspace
    suite.add_case(
        name="Get all projects",
        user_message="Show me all projects in the workspace",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_projects,
                args={},
            ),
        ],
        critics=[],  # No specific args expected
    )

    # Eval Prompt: Show me all issues in the "arcade testing" project
    suite.add_case(
        name="Find issues in arcade testing project",
        user_message='Show me all issues in the "arcade testing" project',
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "project": "arcade testing",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="project", weight=1.0),
        ],
    )

    # Eval Prompt: Find all active projects
    suite.add_case(
        name="Get active projects only",
        user_message="Find all active projects",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_projects,
                args={
                    "status": "started",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="status", weight=1.0),
        ],
    )

    # Eval Prompt: Show me projects for the Backend team
    suite.add_case(
        name="Get Backend team projects",
        user_message="Show me projects for the Backend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_projects,
                args={
                    "team": "Backend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Find completed projects
    suite.add_case(
        name="Get completed projects",
        user_message="Find completed projects",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_projects,
                args={
                    "status": "completed",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="status", weight=1.0),
        ],
    )

    # Eval Prompt: Show me projects created in the last month
    suite.add_case(
        name="Find recently created projects",
        user_message="Show me projects created in the last month",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_projects,
                args={
                    "created_after": "last month",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="created_after", weight=1.0),
        ],
    )

    # Eval Prompt: Find projects that include archived ones
    suite.add_case(
        name="Get all projects including archived",
        user_message="Find projects that include archived ones",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_projects,
                args={
                    "include_archived": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="include_archived", weight=1.0),
        ],
    )

    # Eval Prompt: Show me issues in the Q1 project
    suite.add_case(
        name="Find issues in Q1 project",
        user_message="Show me issues in the Q1 project",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "project": "Q1",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="project", weight=1.0),
        ],
    )

    return suite
