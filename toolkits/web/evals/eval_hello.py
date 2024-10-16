import arcade_web
from arcade_web.tools.hello import hello

from arcade.core.catalog import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    SimilarityCritic,
    tool_eval,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_web)


@tool_eval()
def web_eval_suite():
    suite = EvalSuite(
        name="web Tools Evaluation",
        system_message="You are an AI assistant with access to web tools. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Saying hello",
        user_message="Say hello to the developer!!!!",
        expected_tool_calls=[(hello, {"name": "developer"})],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="name", weight=0.5),
        ],
    )

    return suite
