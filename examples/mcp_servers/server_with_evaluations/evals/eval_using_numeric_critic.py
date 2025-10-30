from arcade_core import ToolCatalog
from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    NumericCritic,
    tool_eval,
)

import server_with_evaluations
from server_with_evaluations.tools import get_n_random_numbers

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()

# Add all of the tools in the server_with_evaluations module to the catalog
catalog.add_module(server_with_evaluations)


@tool_eval()
def server_with_evaluations_numeric_eval_suite() -> EvalSuite:
    """
    Create an evaluation suite for numeric tools using NumericCritic.

    NumericCritic is useful when:
    - Evaluating calculations where exact precision isn't required
    - Cases where numeric values are within an acceptable range
    """
    suite = EvalSuite(
        name="Numeric Tools Evaluation",
        catalog=catalog,
        system_message="You are a helpful assistant for data analysis and statistics.",
        rubric=rubric,
    )

    suite.add_case(
        name="Generate random numbers",
        user_message="Generate some random numbers. Generate at least 10 numbers, but less than or equal to 20 numbers.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_n_random_numbers,
                args={
                    "n": 15,
                },
            )
        ],
        critics=[
            NumericCritic(
                critic_field="n",
                weight=1.0,
                value_range=(10, 20),  # n must be between 10 and 20 inclusive
                match_threshold=1.0,
            ),
        ],
    )

    return suite
