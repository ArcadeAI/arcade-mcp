from arcade_tdk import ToolCatalog
from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_evals.critic import SimilarityCritic

import arcade_gibsonai
from arcade_gibsonai.tools.query import execute_query

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
            "Use them to help the user execute queries against the GibsonAI database. "
            "You can perform all SQL operations including SELECT, INSERT, UPDATE, DELETE, "
            "CREATE, ALTER, DROP, and other schema management operations."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # SELECT query test
    suite.add_case(
        name="Execute SELECT query",
        user_message="Can you run a simple SELECT query to get the current timestamp?",
        expected_tool_calls=[
            ExpectedToolCall(func=execute_query, args={"query": "SELECT NOW()"})
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

    # INSERT query test
    suite.add_case(
        name="Execute INSERT query",
        user_message="Insert a new user with name 'John Doe' and email 'john@example.com' into the users table.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_query,
                args={
                    "query": "INSERT INTO users (name, email) VALUES ('John Doe', 'john@example.com')"
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to add a new user to the database."},
            {
                "role": "assistant",
                "content": "I'll help you insert a new user into the users table.",
            },
        ],
    )

    # UPDATE query test
    suite.add_case(
        name="Execute UPDATE query",
        user_message="Update the user with ID 1 to change their email to 'newemail@example.com'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_query,
                args={
                    "query": "UPDATE users SET email = 'newemail@example.com' WHERE id = 1"
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to update a user's email address."},
            {
                "role": "assistant",
                "content": "I'll help you update the user's email in the database.",
            },
        ],
    )

    # DELETE query test
    suite.add_case(
        name="Execute DELETE query",
        user_message="Delete the user with ID 5 from the users table.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_query, args={"query": "DELETE FROM users WHERE id = 5"}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to remove a user from the database."},
            {
                "role": "assistant",
                "content": "I'll help you delete the user from the users table.",
            },
        ],
    )

    # CREATE TABLE query test
    suite.add_case(
        name="Execute CREATE TABLE query",
        user_message="Create a new table called 'products' with columns: id (integer primary key), name (varchar), price (decimal).",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_query,
                args={
                    "query": "CREATE TABLE products (id INTEGER PRIMARY KEY, name VARCHAR(255), price DECIMAL(10,2))"
                },
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {
                "role": "user",
                "content": "I need to create a new table for storing product information.",
            },
            {
                "role": "assistant",
                "content": "I'll help you create a products table with the specified columns.",
            },
        ],
    )

    # ALTER TABLE query test
    suite.add_case(
        name="Execute ALTER TABLE query",
        user_message="Add a new column 'description' of type TEXT to the products table.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_query,
                args={"query": "ALTER TABLE products ADD COLUMN description TEXT"},
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {
                "role": "user",
                "content": "I need to add a description column to the products table.",
            },
            {
                "role": "assistant",
                "content": "I'll help you alter the products table to add a description column.",
            },
        ],
    )

    # DROP TABLE query test
    suite.add_case(
        name="Execute DROP TABLE query",
        user_message="Drop the temporary_data table as it's no longer needed.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=execute_query, args={"query": "DROP TABLE temporary_data"}
            )
        ],
        rubric=rubric,
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
        ],
        additional_messages=[
            {"role": "user", "content": "I need to remove the temporary_data table."},
            {
                "role": "assistant",
                "content": "I'll help you drop the temporary_data table.",
            },
        ],
    )

    return suite
