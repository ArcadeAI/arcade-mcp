from arcade.core.catalog import ToolCatalog
from arcade_math.tools.arithmetic import add, sqrt

from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


# TODO: add_toolkit didn't work
catalog = ToolCatalog()
catalog.add_tool(add)
catalog.add_tool(sqrt)


@tool_eval("gpt-4o-mini")
def arithmetic_eval_suite():
    suite = EvalSuite(
        name="Math Tools Evaluation",
        system="You are an AI assistant with access to math tools. Use them to help the user with their math-related tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Add two large numbers",
        user_message="Add 12345 and 987654321",
        expected_tool_calls=[
            ExpectedToolCall(
                "Add",
                args={
                    "a": 12345,
                    "b": 987654321,
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(
                critic_field="a", weight=0.5
            ),  # TODO: weight should be optional
            BinaryCritic(critic_field="b", weight=0.5),
        ],
    )

    suite.add_case(
        name="Take the square root of a large number",
        user_message="What is the square root of 3224990521?",
        expected_tool_calls=[ExpectedToolCall(lambda: sqrt(3224990521))],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="a", weight=1.0),
        ],
    )

    return suite
