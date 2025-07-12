import arcade_postgres
from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_postgres.tools.postgres import (
    discover_tables,
    execute_query,
    get_table_schema,
)
from arcade_tdk import ToolCatalog

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_postgres)


@tool_eval()
def sql_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="sql Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to sql tools. "
            "Use them to help the user with their tasks."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get user by id (schema known)",
        user_message="Tell me the name and email of user #1 in my database.  The table 'users' has the following schema: id: int, name: str, email: str, password_hash: str, created_at: datetime, updated_at: datetime",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_query, args={"query": "SELECT name, email FROM users WHERE id = 1"}
            )
        ],
        rubric=rubric,
        critics=[SimilarityCritic(critic_field="query", weight=1.0)],
    )

    suite.add_case(
        name="Discover tables",
        user_message="What tables are in my database?",
        expected_tool_calls=[
            ExpectedToolCall(func=discover_tables, args={}),
        ],
        rubric=rubric,
    )

    suite.add_case(
        name="Get table schema (schema provided)",
        user_message="What columns are in the table 'public.users' in my database?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_table_schema, args={"schema_name": "public", "table_name": "users"}
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="schema_name", weight=0.5),
            BinaryCritic(critic_field="table_name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Get table schema (schema not provided)",
        user_message="What columns are in the table 'users' in my database?",
        additional_messages=[
            {"role": "user", "content": "When not provided, the schema is 'public'."}
        ],
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_table_schema, args={"schema_name": "public", "table_name": "users"}
            ),
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="schema_name", weight=0.5),
            BinaryCritic(critic_field="table_name", weight=0.5),
        ],
    )

    return suite
