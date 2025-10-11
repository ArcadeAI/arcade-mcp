from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import SimilarityCritic
from arcade_tdk import ToolCatalog

import arcade_gibsonai
from arcade_gibsonai.tools.delete import delete_records
from arcade_gibsonai.tools.insert import insert_records
from arcade_gibsonai.tools.query import execute_read_query
from arcade_gibsonai.tools.update import update_records

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_gibsonai)


@tool_eval()
def gibsonai_eval_suite() -> EvalSuite:
    suite = EvalSuite(
        name="GibsonAI Database Tools Evaluation",
        system_message=(
            "You are an AI assistant with access to GibsonAI database tools. "
            "Use them to help the user execute queries and database operations. "
            "For read operations, use execute_read_query. For data modifications, "
            "use the specific parameterized tools: insert_records, update_records, "
            "and delete_records with proper validation."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # SELECT query test (read-only)
    suite.add_case(
        name="Execute SELECT query",
        user_message="Can you run a simple SELECT query to get the current timestamp?",
        expected_tool_calls=[
            ExpectedToolCall(func=execute_read_query, args={"query": "SELECT NOW()"})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to test the database connection."},
            {
                "role": "assistant",
                "content": "I'll help you test the database connection by running a simple query.",
            },
        ],
    )

    # INSERT query test (using parameterized tool)
    suite.add_case(
        name="Execute INSERT operation",
        user_message="Insert a new user with name 'John Doe' and email 'john@example.com' into the users table.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=insert_records,
                args={
                    "table_name": "users",
                    "records": '[{"name": "John Doe", "email": "john@example.com"}]',
                    "on_conflict": "",
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="table_name", weight=0.4),
            SimilarityCritic(critic_field="records", weight=0.6),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to add a new user to the database."},
            {
                "role": "assistant",
                "content": "I'll help you insert a new user into the users table using the parameterized insert tool.",
            },
        ],
    )

    # UPDATE query test (using parameterized tool)
    suite.add_case(
        name="Execute UPDATE operation",
        user_message="Update the user with ID 1 to change their email to 'newemail@example.com'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_records,
                args={
                    "table_name": "users",
                    "updates": '{"email": "newemail@example.com"}',
                    "conditions": '[{"column": "id", "operator": "=", "value": 1}]',
                    "limit": 0,
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="table_name", weight=0.3),
            SimilarityCritic(critic_field="updates", weight=0.4),
            SimilarityCritic(critic_field="conditions", weight=0.3),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to update a user's email address."},
            {
                "role": "assistant",
                "content": "I'll help you update the user's email using the parameterized update tool.",
            },
        ],
    )

    # DELETE query test (using parameterized tool)
    suite.add_case(
        name="Execute DELETE operation",
        user_message="Delete the user with ID 5 from the users table.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=delete_records,
                args={
                    "table_name": "users",
                    "conditions": '[{"column": "id", "operator": "=", "value": 5}]',
                    "limit": 0,
                    "confirm_deletion": True,
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="table_name", weight=0.3),
            SimilarityCritic(critic_field="conditions", weight=0.4),
            SimilarityCritic(critic_field="confirm_deletion", weight=0.3),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to remove a user from the database."},
            {
                "role": "assistant",
                "content": "I'll help you delete the user using the parameterized delete tool with safety confirmation.",
            },
        ],
    )

    # SHOW TABLES test (read-only)
    suite.add_case(
        name="Execute SHOW TABLES query",
        user_message="Show me all the tables in the database.",
        expected_tool_calls=[
            ExpectedToolCall(func=execute_read_query, args={"query": "SHOW TABLES"})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to see what tables exist in the database."},
            {
                "role": "assistant",
                "content": "I'll show you all the tables using a SHOW TABLES query.",
            },
        ],
    )

    # DESCRIBE test (read-only)
    suite.add_case(
        name="Execute DESCRIBE query",
        user_message="Describe the structure of the users table.",
        expected_tool_calls=[
            ExpectedToolCall(func=execute_read_query, args={"query": "DESCRIBE users"})
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to understand the structure of the users table."},
            {
                "role": "assistant",
                "content": "I'll describe the users table structure for you.",
            },
        ],
    )

    # Complex SELECT with JOIN (read-only)
    suite.add_case(
        name="Execute complex SELECT with JOIN",
        user_message="Get all users with their order totals, joining users and orders tables.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_read_query,
                args={
                    "query": "SELECT u.name, u.email, SUM(o.total) as total_orders FROM users u LEFT JOIN orders o ON u.id = o.user_id GROUP BY u.id, u.name, u.email LIMIT 100"
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to analyze user order data."},
            {
                "role": "assistant",
                "content": "I'll create a query that joins users with their orders to show the totals.",
            },
        ],
    )

    return suite
