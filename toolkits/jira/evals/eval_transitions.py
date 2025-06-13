from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_jira
from arcade_jira.critics import (
    CaseInsensitiveBinaryCritic,
)
from arcade_jira.tools.transitions import (
    get_transition_by_status_name,
    get_transitions_available_for_issue,
    transition_issue_to_new_status,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_jira)


@tool_eval()
def transitions_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Transitions eval suite",
        system_message=(
            "You are an AI assistant with access to Jira tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get transitions available for issue",
        user_message="Get the transitions available for the issue ENG-123.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_transitions_available_for_issue,
                args={
                    "issue": "ENG-123",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=1),
        ],
    )

    suite.add_case(
        name="Can I transition an issue to status 'Done'?",
        user_message="Can I transition the issue ENG-123 to the status 'Done'?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_transitions_available_for_issue,
                args={
                    "issue": "ENG-123",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=1),
        ],
    )

    suite.add_case(
        name="Get transition by status name",
        user_message="Get the transition for the issue ENG-123 and status 'Done'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_transition_by_status_name,
                args={
                    "issue": "ENG-123",
                    "transition": "Done",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="transition", weight=0.5),
        ],
    )

    suite.add_case(
        name="Transition issue to a new status",
        user_message="Transition the issue ENG-123 to the status 'Done'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=transition_issue_to_new_status,
                args={
                    "issue": "ENG-123",
                    "transition": "Done",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="transition", weight=0.5),
        ],
    )

    suite.add_case(
        name="Mark issue as done",
        user_message="Mark the issue ENG-123 as done.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=transition_issue_to_new_status,
                args={
                    "issue": "ENG-123",
                    "transition": "Done",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="transition", weight=0.5),
        ],
    )

    suite.add_case(
        name="Update issue with new status",
        user_message="Update the issue ENG-123 status to in progress.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=transition_issue_to_new_status,
                args={
                    "issue": "ENG-123",
                    "transition": "in progress",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            CaseInsensitiveBinaryCritic(critic_field="issue", weight=0.5),
            CaseInsensitiveBinaryCritic(critic_field="transition", weight=0.5),
        ],
    )

    return suite
