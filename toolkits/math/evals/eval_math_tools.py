from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_math
from arcade_math.tools.arithmetic import (
    add,
    divide,
    mod,
    multiply,
    subtract,
    sum_list,
    sum_range,
)
from arcade_math.tools.exponents import (
    log,
    power,
)
from arcade_math.tools.miscellaneous import (
    abs_val,
    factorial,
    sqrt,
)
from arcade_math.tools.rational import (
    gcd,
    lcm,
)
from arcade_math.tools.rounding import (
    ceil,
    floor,
    round_num,
)
from arcade_math.tools.statistics import (
    avg,
    median,
)
from arcade_math.tools.trigonometry import (
    deg_to_rad,
    rad_to_deg,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_math)


@tool_eval()
def math_eval_suite():
    suite = EvalSuite(
        name="Math Tools Evaluation",
        system_message="You're an AI assistant with access to math tools. Use them to help the user with their math-related tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    list_param = ["1", "2", "3", "4", "5"]
    funcs_to_expression_and_params = [
        # unary
        (sqrt, "What's the square root of {a}?", {"a": "25"}),
        (abs_val, "What's the absolute value of {a}?", {"a": "-10"}),
        (factorial, "What's the factorial of {a}?", {"a": "5"}),
        (deg_to_rad, "Convert {degrees} from degrees to radians", {"degrees": "180"}),
        (rad_to_deg, "Convert {radians} from radias to degrees", {"radians": "3.14"}),
        (ceil, "Compute the ceiling of {a}", {"a": "3.14"}),
        (floor, "Compute the floor of {a}", {"a": "3.14"}),
        # binary
        (add, "Add {a} and {b}", {"a": "12345", "b": "987654321"}),
        (subtract, "Subtract {b} from {a}", {"a": "987654321", "b": "12345"}),
        (multiply, "Multiply {a} and {b}", {"a": "12345", "b": "567890"}),
        (divide, "What is {a} divided by {b}?", {"a": "1234123479", "b": "123"}),
        (
            sum_range,
            "What's the sum of all numbers from {start} to {end}?",
            {"start": "10", "end": "345"},
        ),
        (mod, "What's the remainder of dividing {a} by {b}?", {"a": "234", "b": "17"}),
        (power, "Raise {a} to the power of {b}", {"a": "2", "b": "8"}),
        (log, "What's the logarithm of {a} with base {base}?", {"a": "8", "base": "2"}),
        (
            round_num,
            "Round {value} to {ndigits} decimal places",
            {"value": "12.23746234", "ndigits": "3"},
        ),
        (gcd, "Find the greatest common divisor of {a} and {b}", {"a": "50", "b": "10"}),
        (lcm, "FInd the least common multiple of {a} and {b}", {"a": "7", "b": "13"}),
        # n-nary
        (
            sum_list,
            f"Calculate the sum of these numbers: {' '.join(list_param)}",
            {"numbers": list_param},
        ),
        (
            avg,
            f"Find the average of these numbers: {' '.join(list_param)}",
            {"numbers": list_param},
        ),
        (
            median,
            f"Find the median of these numbers: {' '.join(list_param)}",
            {"numbers": list_param},
        ),
    ]

    for func, expression, params in funcs_to_expression_and_params:
        parametrized_expression = expression.format(**params)
        num_params = len(params)
        suite.add_case(
            name=parametrized_expression,
            user_message=parametrized_expression,
            expected_tool_calls=[
                ExpectedToolCall(
                    func=func,
                    args=params,
                )
            ],
            rubric=rubric,
            critics=[BinaryCritic(critic_field=param, weight=1.0 / num_params) for param in params],
        )

    return suite
