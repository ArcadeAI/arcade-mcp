from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_asana
from arcade_asana.tools import (
    create_task,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_asana)


@tool_eval()
def create_task_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="create task eval suite",
        system_message="You are an AI assistant with access to Asana tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Create task with name, description, start and due dates",
        user_message="Create a task with the name 'Hello World' and the description 'This is a task description' starting on 2025-05-05 and due on 2025-05-11.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_task,
                args={
                    "name": "Hello World",
                    "description": "This is a task description",
                    "start_date": "2025-05-05",
                    "due_date": "2025-05-11",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="name", weight=1 / 4),
            BinaryCritic(critic_field="description", weight=1 / 4),
            BinaryCritic(critic_field="start_date", weight=1 / 4),
            BinaryCritic(critic_field="due_date", weight=1 / 4),
        ],
    )

    suite.add_case(
        name="Create task with name and tag names",
        user_message="Create a task with the name 'Hello World' and the tags 'My Tag' and 'My Other Tag'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_task,
                args={
                    "name": "Hello World",
                    "tags": ["My Tag", "My Other Tag"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="name", weight=0.5),
            BinaryCritic(critic_field="tags", weight=0.5),
        ],
    )

    suite.add_case(
        name="Create task with name and tag IDs",
        user_message="Create a task with the name 'Hello World' and the tags '1234567890' and '1234567891'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_task,
                args={
                    "name": "Hello World",
                    "tags": ["1234567890", "1234567891"],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="name", weight=0.5),
            BinaryCritic(critic_field="tags", weight=0.5),
        ],
    )

    return suite
