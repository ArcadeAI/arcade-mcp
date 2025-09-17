# RUN ME WITH `uv run arcade evals evals --host api.arcade.dev`

import arcade_mongodb
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_mongodb.tools.mongodb import (
    aggregate_documents,
    count_documents,
    discover_collections,
    discover_databases,
    find_documents,
    get_collection_schema,
)
from arcade_tdk import ToolCatalog

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_mongodb)


@tool_eval()
def mongodb_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="MongoDB Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to MongoDB tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Discover databases",
        user_message="What databases are available in my MongoDB instance?",
        expected_tool_calls=[
            ExpectedToolCall(func=discover_databases, args={}),
        ],
        rubric=rubric,
    )

    suite.add_case(
        name="Discover collections",
        user_message="What collections are in the 'admin' database?",
        expected_tool_calls=[
            ExpectedToolCall(func=discover_collections, args={"database_name": "admin"}),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="database_name", weight=1.0),
        ],
    )

    suite.add_case(
        name="Get collection schema (single tool call)",
        user_message="Get the schema of the 'system.users' collection in the 'admin' database.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_collection_schema,
                args={"database_name": "admin", "collection_name": "system.users"},
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="database_name", weight=0.5),
            BinaryCritic(critic_field="collection_name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Find documents (direct call)",
        user_message="Find documents in the 'startup_log' collection of the 'local' database, limited to 5 results.",
        additional_messages=[
            {
                "role": "user",
                "content": "You can call find_documents directly without discovering collections first for this test.",
            }
        ],
        expected_tool_calls=[
            ExpectedToolCall(
                func=find_documents,
                args={
                    "database_name": "local",
                    "collection_name": "startup_log",
                    "limit": 5,
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="database_name", weight=0.33),
            BinaryCritic(critic_field="collection_name", weight=0.33),
            BinaryCritic(critic_field="limit", weight=0.34),
        ],
    )

    suite.add_case(
        name="Count documents",
        user_message="Count all documents in the 'startup_log' collection of the 'local' database.",
        additional_messages=[
            {
                "role": "user",
                "content": "You can call count_documents directly without discovering collections first for this test.",
            }
        ],
        expected_tool_calls=[
            ExpectedToolCall(
                func=count_documents,
                args={
                    "database_name": "local",
                    "collection_name": "startup_log",
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="database_name", weight=0.5),
            BinaryCritic(critic_field="collection_name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Count documents with filter",
        user_message="Count documents in the 'startup_log' collection of the 'local' database where the level is 'INFO'.",
        additional_messages=[
            {
                "role": "user",
                "content": "You can call count_documents directly without discovering collections first for this test.",
            }
        ],
        expected_tool_calls=[
            ExpectedToolCall(
                func=count_documents,
                args={
                    "database_name": "local",
                    "collection_name": "startup_log",
                    "filter_dict": '{"level": "INFO"}',
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="database_name", weight=0.25),
            BinaryCritic(critic_field="collection_name", weight=0.25),
            SimilarityCritic(critic_field="filter_dict", weight=0.5),
        ],
    )

    suite.add_case(
        name="Aggregate documents",
        user_message="Group documents in the 'startup_log' collection of the 'local' database by level and count them.",
        additional_messages=[
            {
                "role": "user",
                "content": "You can call aggregate_documents directly without discovering collections first for this test.",
            }
        ],
        expected_tool_calls=[
            ExpectedToolCall(
                func=aggregate_documents,
                args={
                    "database_name": "local",
                    "collection_name": "startup_log",
                    "pipeline": [
                        '{"$group": {"_id": "$level", "count": {"$sum": 1}}}',
                    ],
                },
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="database_name", weight=0.2),
            BinaryCritic(critic_field="collection_name", weight=0.2),
            SimilarityCritic(critic_field="pipeline", weight=0.6),
        ],
    )

    return suite
