from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_notion_toolkit
from arcade_notion_toolkit.enums import ObjectType
from arcade_notion_toolkit.tools import (
    get_object_metadata,
    get_workspace_structure,
    search_by_title,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
catalog.add_module(arcade_notion_toolkit)

# Additional messages
TOOL_CALLING_CONVERSATION = [
    {"role": "user", "content": "hi"},
    {"role": "assistant", "content": "Hello! How can I assist you today?"},
    {"role": "user", "content": "explain LLM tool calling"},
    {
        "role": "assistant",
        "content": "Tool calling in the context of Large Language Models (LLMs) refers to the process where the model uses external tools, plugins, orfunctions to gather, process, or enhance information. This allows the model to access more current or specific data and perform actions that are beyond itstrained capabilities.\n\nHere's a breakdown of how this works:\n\n1. **Identification of Needs**: The LLM can identify when a task or query requires dataor actions that are not within its built-in knowledge. This could be due to the data being too recent, too specialized, or involving actions that requireinterfacing with external systems.\n\n2. **Tool Selection**: The LLM selects appropriate tools or functions that are registered and permitted for use. Thisselection is based on the task's requirements, such as retrieving data, performing calculations, or managing content.\n\n3. **Parameter Configuration**:The LLM prepares the necessary input parameters for the tools. These parameters tell the tools what specific actions to take or what data toretrieve.\n\n4. **Execution**: The tools are executed. Some tools run asynchronously, allowing the LLM to perform other tasks while waiting for theresults.\n\n5. **Result Integration**: The LLM integrates the results from the tools back into the conversation or task. It uses this information to answerquestions, perform further analysis, or update content as needed.\n\n6. **Feedback Loop**: Often, the results are looped back into the model's reasoningprocess, which can then adjust its line of questioning or actions based on the new data.\n\nThis system enhances the LLM's flexibility, making itapplicable to a wider range of real-world applications by utilizing up-to-date and specialized information through these tools.",  # noqa: E501
    },
]


@tool_eval()
def search_by_title_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools searching for objects by title."""
    suite = EvalSuite(
        name="Notion Search Tools Evaluation",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Easy case
    suite.add_case(
        name="Search by title easy difficulty",
        user_message="Search for my page with the title 'Daily Standup'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_by_title,
                args={
                    "query": "Daily Standup",
                    "select": ObjectType.PAGE,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.6, similarity_threshold=0.95),
            BinaryCritic(critic_field="select", weight=0.4),
        ],
    )

    # Medium case
    suite.add_case(
        name="Search by title medium difficulty",
        user_message=(
            "so i was just thinking about LLMs and how to create an agent. "
            "I remember that tools are important for some reason. "
            "do i have a page or db about tool calling?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_by_title,
                args={
                    "query": "tool calling",
                    "select": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.6),
            BinaryCritic(critic_field="select", weight=0.4),
        ],
    )

    # Hard case
    suite.add_case(
        name="Search by title hard difficulty",
        user_message=(
            "do i have any notes about any of those breakdown points? "
            "Actually, do I have any notes about the 2nd, 3rd, or 5th points?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_by_title,
                args={
                    "query": "Tool Selection",
                    "select": None,
                },
            ),
            ExpectedToolCall(
                func=search_by_title,
                args={
                    "query": "Parameter Configuration",
                    "select": None,
                },
            ),
            ExpectedToolCall(
                func=search_by_title,
                args={
                    "query": "Result Integration",
                    "select": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="query", weight=0.8),
            BinaryCritic(critic_field="select", weight=0.2),
        ],
        additional_messages=TOOL_CALLING_CONVERSATION,
    )

    return suite


@tool_eval()
def get_object_metadata_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting object metadata."""
    suite = EvalSuite(
        name="Notion Get Object Metadata Evaluation",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Easy case
    suite.add_case(
        name="Get object metadata easy difficulty",
        user_message="Get any metadata about my page with the title 'Daily Standup'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_object_metadata,
                args={
                    "object_title": "Daily Standup",
                    "object_type": ObjectType.PAGE,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="object_title", weight=0.8, similarity_threshold=0.95),
            BinaryCritic(critic_field="object_type", weight=0.2),
        ],
    )

    # Medium case
    suite.add_case(
        name="Get object metadata medium difficulty",
        user_message="Get the id, url, and last edited time of 'Daily Standup'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_object_metadata,
                args={
                    "object_title": "Daily Standup",
                    "object_type": None,
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="object_title", weight=0.8, similarity_threshold=0.95),
            BinaryCritic(critic_field="object_type", weight=0.2),
        ],
    )

    # Hard case
    suite.add_case(
        name="Get object metadata hard difficulty",
        user_message=(
            "oh I have page about that second point. "
            "This page here https://www.notion.so/be633bf1dfa0436db259571129a590e5. "
            "When was it created?"
        ),
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_object_metadata,
                args={
                    "object_id": "be633bf1dfa0436db259571129a590e5",
                    "object_type": ObjectType.PAGE,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="object_id", weight=0.8),
            BinaryCritic(critic_field="object_type", weight=0.2),
        ],
        additional_messages=TOOL_CALLING_CONVERSATION,
    )

    return suite


@tool_eval()
def get_workspace_structure_eval_suite() -> EvalSuite:
    """Create an evaluation suite for tools getting the workspace structure."""
    suite = EvalSuite(
        name="Notion Get Workspace Structure Evaluation",
        system_message=(
            "You are an AI assistant that has access to the user's Notion workspace. "
            "You can take actions on the user's Notion workspace on behalf of the user."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Easy case
    suite.add_case(
        name="Get workspace structure easy difficulty",
        user_message="Get my workspace tree structure",
        expected_tool_calls=[
            ExpectedToolCall(func=get_workspace_structure, args={}),
        ],
    )

    # Medium case
    suite.add_case(
        name="Get workspace structure medium difficulty",
        user_message="I'm trying to figure out where my 'Daily Standup' page is. "
        "Can you help me find it?",
        expected_tool_calls=[
            ExpectedToolCall(func=get_workspace_structure, args={}),
        ],
    )

    # Hard case
    suite.add_case(
        name="Get workspace structure hard difficulty",
        user_message="list pages that are subpages of my 'Daily Standup' page",
        expected_tool_calls=[
            ExpectedToolCall(func=get_workspace_structure, args={}),
        ],
    )
    return suite
