"""
Comprehensive evaluation suite for Linear workflow management tools.
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
from arcade_linear.tools.workflows import (
    get_workflow_states,
    create_workflow_state,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def get_workflow_states_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for get_workflow_states tool"""
    suite = EvalSuite(
        name="Get Workflow States Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user manage Linear workflow states and team processes."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Show me all workflow states for the Frontend team
    suite.add_case(
        name="Get Frontend team workflow states",
        user_message="Show me all workflow states for the Frontend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_workflow_states,
                args={
                    "team": "Frontend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: What statuses are available for the Backend team?
    suite.add_case(
        name="Get Backend team available statuses",
        user_message="What statuses are available for the Backend team?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_workflow_states,
                args={
                    "team": "Backend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: List all workflow states for the test team
    suite.add_case(
        name="Get test team workflow states",
        user_message="List all workflow states for the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_workflow_states,
                args={
                    "team": "test",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Show me the workflow for the Product team
    suite.add_case(
        name="Get Product team workflow",
        user_message="Show me the workflow for the Product team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_workflow_states,
                args={
                    "team": "Product",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: What are the available statuses for the Design team?
    suite.add_case(
        name="Get Design team available statuses",
        user_message="What are the available statuses for the Design team?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_workflow_states,
                args={
                    "team": "Design",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Check workflow states for the QA team
    suite.add_case(
        name="Check QA team workflow states",
        user_message="Check workflow states for the QA team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_workflow_states,
                args={
                    "team": "QA",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    return suite


@tool_eval()
def create_workflow_state_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for create_workflow_state tool"""
    suite = EvalSuite(
        name="Create Workflow State Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user create and manage Linear workflow states."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Create a new "In Review" status for the Frontend team
    suite.add_case(
        name="Create In Review status for Frontend",
        user_message="Create a new workflow state called \"In Review\" for the Frontend team as a started type",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "Frontend",
                    "name": "In Review",
                    "type": "started",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.4),
            BinaryCritic(critic_field="name", weight=0.4),
            BinaryCritic(critic_field="type", weight=0.2),
        ],
    )

    # Eval Prompt: Add a "Ready for QA" state to the Backend team workflow
    suite.add_case(
        name="Add Ready for QA state to Backend",
        user_message="Create a new workflow state \"Ready for QA\" for the Backend team as started type",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "Backend",
                    "name": "Ready for QA",
                    "type": "started",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.4),
            BinaryCritic(critic_field="name", weight=0.4),
            BinaryCritic(critic_field="type", weight=0.2),
        ],
    )

    # Eval Prompt: Create a "Blocked" status for the test team that shows when work is halted
    suite.add_case(
        name="Create Blocked status with description",
        user_message="Create a workflow state called \"Blocked\" for the test team with type started and description \"when work is halted\"",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "test",
                    "name": "Blocked",
                    "type": "started",
                    "description": "when work is halted",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.3),
            BinaryCritic(critic_field="name", weight=0.3),
            BinaryCritic(critic_field="type", weight=0.2),
            SimilarityCritic(critic_field="description", weight=0.2),
        ],
    )

    # Eval Prompt: Add a "Needs Approval" backlog state to the Product team
    suite.add_case(
        name="Create Needs Approval backlog state",
        user_message="Add a \"Needs Approval\" backlog state to the Product team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "Product",
                    "name": "Needs Approval",
                    "type": "backlog",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.4),
            BinaryCritic(critic_field="name", weight=0.4),
            BinaryCritic(critic_field="type", weight=0.2),
        ],
    )

    # Eval Prompt: Create a "Design Complete" completed status for the Design team with blue color
    suite.add_case(
        name="Create Design Complete status with color",
        user_message="Create a \"Design Complete\" completed status for the Design team with blue color",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "Design",
                    "name": "Design Complete",
                    "type": "completed",
                    "color": "#3b82f6",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.3),
            BinaryCritic(critic_field="name", weight=0.3),
            BinaryCritic(critic_field="type", weight=0.2),
            SimilarityCritic(critic_field="color", weight=0.2),
        ],
    )

    # Eval Prompt: Add a "Won't Fix" canceled state to the QA team
    suite.add_case(
        name="Create Won't Fix canceled state",
        user_message="Add a \"Won't Fix\" canceled state to the QA team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "QA",
                    "name": "Won't Fix",
                    "type": "canceled",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.4),
            BinaryCritic(critic_field="name", weight=0.4),
            BinaryCritic(critic_field="type", weight=0.2),
        ],
    )

    # Eval Prompt: Create a "Pending Review" started state for the Backend team at position 3
    suite.add_case(
        name="Create Pending Review state with position",
        user_message="Create a \"Pending Review\" started state for the Backend team at position 3",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "Backend",
                    "name": "Pending Review",
                    "type": "started",
                    "position": 3.0,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.3),
            BinaryCritic(critic_field="name", weight=0.3),
            BinaryCritic(critic_field="type", weight=0.2),
            BinaryCritic(critic_field="position", weight=0.2),
        ],
    )

    # Eval Prompt: Add a "Needs Refinement" unstarted state to the Product team for issues that need more planning
    suite.add_case(
        name="Create Needs Refinement unstarted state with description",
        user_message="Add a \"Needs Refinement\" unstarted state to the Product team for issues that need more planning",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_workflow_state,
                args={
                    "team": "Product",
                    "name": "Needs Refinement",
                    "type": "unstarted",
                    "description": "issues that need more planning",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.3),
            BinaryCritic(critic_field="name", weight=0.3),
            BinaryCritic(critic_field="type", weight=0.2),
            SimilarityCritic(critic_field="description", weight=0.2),
        ],
    )

    return suite 