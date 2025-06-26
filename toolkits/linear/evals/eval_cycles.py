"""
Comprehensive evaluation suite for Linear cycle/sprint management tools.
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
from arcade_linear.tools.cycles import (
    get_current_cycle,
    list_cycles,
    get_cycle_issues,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def get_current_cycle_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for get_current_cycle tool"""
    suite = EvalSuite(
        name="Get Current Cycle Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user manage Linear cycles and sprint planning."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: What's the current sprint for the Frontend team?
    suite.add_case(
        name="Get Frontend current sprint",
        user_message="What's the current sprint for the Frontend team?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_current_cycle,
                args={
                    "team": "Frontend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Show me the active cycle for the Backend team
    suite.add_case(
        name="Get Backend active cycle",
        user_message="Show me the active cycle for the Backend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_current_cycle,
                args={
                    "team": "Backend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: What cycle is the Product team currently in?
    suite.add_case(
        name="Get Product team current cycle",
        user_message="What cycle is the Product team currently in?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_current_cycle,
                args={
                    "team": "Product",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Check the current sprint for the test team
    suite.add_case(
        name="Check test team current sprint",
        user_message="Check the current sprint for the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_current_cycle,
                args={
                    "team": "test",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: What's the current cycle for the Design team?
    suite.add_case(
        name="Get Design team current cycle",
        user_message="What's the current cycle for the Design team?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_current_cycle,
                args={
                    "team": "Design",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Show the active sprint for QA team
    suite.add_case(
        name="Get QA team active sprint",
        user_message="Show the active sprint for QA team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_current_cycle,
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
def list_cycles_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for list_cycles tool"""
    suite = EvalSuite(
        name="List Cycles Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user manage Linear cycles and sprint planning."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Show me all active cycles for the Frontend team
    suite.add_case(
        name="List Frontend active cycles",
        user_message="Show me all active cycles for the Frontend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_cycles,
                args={
                    "team": "Frontend",
                    "active_only": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.7),
            BinaryCritic(critic_field="active_only", weight=0.3),
        ],
    )

    # Eval Prompt: List all cycles for the Backend team including completed ones
    suite.add_case(
        name="List all Backend cycles including completed",
        user_message="List all cycles for the Backend team including completed ones",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_cycles,
                args={
                    "team": "Backend",
                    "active_only": False,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.7),
            BinaryCritic(critic_field="active_only", weight=0.3),
        ],
    )

    # Eval Prompt: Show me the last 5 cycles for the Product team
    suite.add_case(
        name="List last 5 Product cycles",
        user_message="Show me the last 5 cycles for the Product team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_cycles,
                args={
                    "team": "Product",
                    "active_only": False,
                    "limit": 5,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.5),
            BinaryCritic(critic_field="active_only", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    # Eval Prompt: Get all sprints for the test team
    suite.add_case(
        name="Get all test team sprints",
        user_message="Get all sprints for the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_cycles,
                args={
                    "team": "test",
                    "active_only": False,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.7),
            BinaryCritic(critic_field="active_only", weight=0.3),
        ],
    )

    # Eval Prompt: Show me the first 3 active cycles for the Design team
    suite.add_case(
        name="List first 3 Design active cycles",
        user_message="Show me the first 3 active cycles for the Design team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_cycles,
                args={
                    "team": "Design",
                    "active_only": True,
                    "limit": 3,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.5),
            BinaryCritic(critic_field="active_only", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    # Eval Prompt: List recent cycles for the QA team
    suite.add_case(
        name="List recent QA cycles",
        user_message="List recent cycles for the QA team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_cycles,
                args={
                    "team": "QA",
                    "active_only": False,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.7),
            BinaryCritic(critic_field="active_only", weight=0.3),
        ],
    )

    # Eval Prompt: Show me 10 cycles for the Backend team
    suite.add_case(
        name="List 10 Backend cycles",
        user_message="Show me 10 cycles for the Backend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_cycles,
                args={
                    "team": "Backend",
                    "active_only": False,
                    "limit": 10,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=0.5),
            BinaryCritic(critic_field="active_only", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    return suite


@tool_eval()
def get_cycle_issues_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for get_cycle_issues tool"""
    suite = EvalSuite(
        name="Get Cycle Issues Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user manage Linear cycles and sprint planning."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: What issues are in Sprint 23?
    suite.add_case(
        name="Get Sprint 23 issues",
        user_message="What issues are in Sprint 23?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "Sprint 23",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="cycle", weight=1.0),
        ],
    )

    # Eval Prompt: Show me all issues in the current Frontend cycle
    suite.add_case(
        name="Get Frontend current cycle issues",
        user_message="Show me all issues in the current Frontend cycle",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "current",
                    "team": "Frontend",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="cycle", weight=0.6),
            BinaryCritic(critic_field="team", weight=0.4),
        ],
    )

    # Eval Prompt: List issues in Sprint 24 for the Backend team
    suite.add_case(
        name="Get Backend Sprint 24 issues",
        user_message="List issues in Sprint 24 for the Backend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "Sprint 24",
                    "team": "Backend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="cycle", weight=0.6),
            BinaryCritic(critic_field="team", weight=0.4),
        ],
    )

    # Eval Prompt: Show me the first 20 issues in Cycle 5
    suite.add_case(
        name="Get first 20 issues in Cycle 5",
        user_message="Show me the first 20 issues in Cycle 5",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "Cycle 5",
                    "limit": 20,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="cycle", weight=0.7),
            BinaryCritic(critic_field="limit", weight=0.3),
        ],
    )

    # Eval Prompt: What's in the Q1 Sprint for the Product team?
    suite.add_case(
        name="Get Product Q1 Sprint issues",
        user_message="What's in the Q1 Sprint for the Product team?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "Q1 Sprint",
                    "team": "Product",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="cycle", weight=0.6),
            BinaryCritic(critic_field="team", weight=0.4),
        ],
    )

    # Eval Prompt: List all issues in the Alpha cycle
    suite.add_case(
        name="Get Alpha cycle issues",
        user_message="List all issues in the Alpha cycle",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "Alpha",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="cycle", weight=1.0),
        ],
    )

    # Eval Prompt: Show me 30 issues from Sprint 22 for the test team
    suite.add_case(
        name="Get 30 test team Sprint 22 issues",
        user_message="Show me 30 issues from Sprint 22 for the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "Sprint 22",
                    "team": "test",
                    "limit": 30,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="cycle", weight=0.5),
            BinaryCritic(critic_field="team", weight=0.3),
            BinaryCritic(critic_field="limit", weight=0.2),
        ],
    )

    # Eval Prompt: What issues are in the Design team's Beta cycle?
    suite.add_case(
        name="Get Design Beta cycle issues",
        user_message="What issues are in the Design team's Beta cycle?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_cycle_issues,
                args={
                    "cycle": "Beta",
                    "team": "Design",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="cycle", weight=0.6),
            BinaryCritic(critic_field="team", weight=0.4),
        ],
    )

    return suite 