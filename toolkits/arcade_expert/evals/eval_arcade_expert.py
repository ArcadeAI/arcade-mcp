from arcade.sdk import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)

import arcade_arcade_expert
from arcade_arcade_expert.tools import search_documentation

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_arcade_expert)


@tool_eval()
def arcade_expert_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="Search Documentation Tool Evaluation",
        system_message="Help the user with their queries",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Finding engine.yaml location",
        user_message="where is my engine.yaml file that Arcade is telling me that I need",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_documentation,
                args={"query": "engine.yaml file location"},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.3, similarity_threshold=0.4),
        ],
    )

    suite.extend_case(
        name="Add a custom Reddit OAuth Provider",
        user_message="I want to create a new Reddit OAuth Provider. How do I do this?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_documentation, args={"query": "create a new Reddit OAuth Provider"}
            ),
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.3, similarity_threshold=0.4),
        ],
    )

    return suite
