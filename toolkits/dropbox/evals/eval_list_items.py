from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_dropbox
from arcade_dropbox.critics import DropboxPathCritic
from arcade_dropbox.tools.browse import list_items_in_folder

rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
catalog.add_module(arcade_dropbox)


@tool_eval()
def list_items_in_folder_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the list_items_in_folder tool."""
    suite = EvalSuite(
        name="list_items_in_folder",
        system_message="You are an AI assistant that can interact with files and folders in Dropbox using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="List items in the Dropbox root folder",
        user_message="List the items in the Dropbox root folder",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_items_in_folder,
                args={
                    "folder_path": "",
                    "limit": 100,
                    "cursor": None,
                },
            ),
        ],
        critics=[
            DropboxPathCritic(critic_field="folder_path", weight=0.6),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="cursor", weight=0.2),
        ],
    )

    suite.add_case(
        name="List items in a sub-folder",
        user_message="List the items in the folder AcmeInc/Reports",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_items_in_folder,
                args={
                    "folder_path": "/AcmeInc/Reports",
                    "limit": 100,
                    "cursor": None,
                },
            ),
        ],
        critics=[
            DropboxPathCritic(critic_field="folder_path", weight=0.6),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="cursor", weight=0.2),
        ],
    )

    suite.add_case(
        name="List items in a sub-folder with custom limit",
        user_message="List the first 50 items in the folder AcmeInc/Reports",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_items_in_folder,
                args={
                    "folder_path": "/AcmeInc/Reports",
                    "limit": 50,
                    "cursor": None,
                },
            ),
        ],
        critics=[
            DropboxPathCritic(critic_field="folder_path", weight=0.4),
            BinaryCritic(critic_field="limit", weight=0.4),
            BinaryCritic(critic_field="cursor", weight=0.2),
        ],
    )

    return suite
