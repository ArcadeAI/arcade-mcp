from arcade_core import ToolCatalog
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import server_with_evaluations
from server_with_evaluations.tools import greet

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()

# Add all of the tools in the server_with_evaluations module to the catalog
catalog.add_module(server_with_evaluations)


@tool_eval()
def server_with_evaluations_binary_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the greet tool using the BinaryCritic."""
    suite = EvalSuite(
        name="MCP Server Evaluation",
        catalog=catalog,
        system_message="You are a helpful assistant.",
        rubric=rubric,
    )

    suite.add_case(
        name="Easy Case - Explicitly greet Alice",
        user_message="Greet Alice",
        expected_tool_calls=[
            ExpectedToolCall(
                func=greet,
                args={
                    "name": "Alice",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="name", weight=1.0),
        ],
    )

    suite.add_case(
        name="Implicitly tell the model to greet Bob",
        user_message="Can you greet the other person now, please",
        expected_tool_calls=[
            ExpectedToolCall(
                func=greet,
                args={
                    "name": "Bob",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="name", weight=1.0),
        ],
        additional_messages=[  # Simulate a conversation that happened before this eval case
            {
                "role": "user",
                "content": "I'm here with Alice and Bob. Please greet Alice.",
            },
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_exyK4LmJEHSDn1Xw5oVfS9Xx",
                        "type": "function",
                        "function": {
                            "name": "ServerWithEvaluations_Greet",
                            "arguments": '{"name":"Alice"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "content": "Hello, Alice!",
                "tool_call_id": "call_exyK4LmJEHSDn1Xw5oVfS9Xx",
                "name": "ServerWithEvaluations_Greet",
            },
            {
                "role": "assistant",
                "content": "Hello, Alice!",
            },
        ],
    )

    return suite
