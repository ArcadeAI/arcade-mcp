import arcade_search_engine
from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import SimilarityCritic
from arcade_search_engine.tools.hello import say_hello
from arcade_tdk import ToolCatalog

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_search_engine)


@tool_eval()
def search_engine_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="search_engine Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to search_engine tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Saying hello",
        user_message="He's actually right here, say hi to him!",
        expected_tool_calls=[ExpectedToolCall(func=say_hello, args={"name": "John Doe"})],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="name", weight=0.5),
        ],
        additional_messages=[
            {"role": "user", "content": "My friend's name is John Doe."},
            {"role": "assistant", "content": "It is great that you have a friend named John Doe!"},
        ],
    )

    return suite
