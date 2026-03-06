from arcade_core import ToolCatalog
from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)

import {{ package_name }}
from {{ package_name }}.tools.sample import get_my_reddit_profile

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module({{ package_name }})


@tool_eval()
def {{ toolkit_name }}_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="{{ toolkit_name }} Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to {{ toolkit_name }} tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get my Reddit profile",
        user_message="What is my Reddit username and karma?",
        expected_tool_calls=[ExpectedToolCall(func=get_my_reddit_profile, args={})],
        rubric=rubric,
    )

    return suite
