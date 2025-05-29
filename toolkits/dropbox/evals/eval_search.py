from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_dropbox
from arcade_dropbox.constants import ItemCategory
from arcade_dropbox.critics import DropboxPathCritic
from arcade_dropbox.tools.browse import search_files_and_folders

rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
catalog.add_module(arcade_dropbox)


@tool_eval()
def search_files_and_folders_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the search_files_and_folders tool."""
    suite = EvalSuite(
        name="list_items_in_folder",
        system_message="You are an AI assistant that can interact with files and folders in Dropbox using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Search for files about 'quarterly report' in my Dropbox",
        user_message="Search for files about 'quarterly report' in my Dropbox",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_files_and_folders,
                args={
                    "keywords": "quarterly report",
                    "search_in_folder_path": None,
                    "filter_by_category": None,
                    "limit": 100,
                    "cursor": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.6),
            BinaryCritic(critic_field="search_in_folder_path", weight=0.1),
            BinaryCritic(critic_field="filter_by_category", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="cursor", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for files about 'quarterly report' in a sub-folder",
        user_message="Search for files about 'quarterly report' in the folder AcmeInc/Reports",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_files_and_folders,
                args={
                    "keywords": "quarterly report",
                    "search_in_folder_path": "/AcmeInc/Reports",
                    "filter_by_category": None,
                    "limit": 100,
                    "cursor": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.35),
            DropboxPathCritic(critic_field="search_in_folder_path", weight=0.35),
            BinaryCritic(critic_field="filter_by_category", weight=0.1),
            BinaryCritic(critic_field="limit", weight=0.1),
            BinaryCritic(critic_field="cursor", weight=0.1),
        ],
    )

    suite.add_case(
        name="Search for PDF files about 'quarterly report' in a sub-folder",
        user_message="Search for PDF files about 'quarterly report' in the folder AcmeInc/Reports",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_files_and_folders,
                args={
                    "keywords": "quarterly report",
                    "search_in_folder_path": "/AcmeInc/Reports",
                    "filter_by_category": [ItemCategory.PDF.value],
                    "limit": 100,
                    "cursor": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.25),
            DropboxPathCritic(critic_field="search_in_folder_path", weight=0.25),
            BinaryCritic(critic_field="filter_by_category", weight=0.25),
            BinaryCritic(critic_field="limit", weight=0.125),
            BinaryCritic(critic_field="cursor", weight=0.125),
        ],
    )

    suite.add_case(
        name="Search for PDF files about 'quarterly report' in a sub-folder",
        user_message="Return the first 10 PDF files about 'quarterly report' in the folder AcmeInc/Reports",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_files_and_folders,
                args={
                    "keywords": "quarterly report",
                    "search_in_folder_path": "/AcmeInc/Reports",
                    "filter_by_category": [ItemCategory.PDF.value],
                    "limit": 10,
                    "cursor": None,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.2),
            DropboxPathCritic(critic_field="search_in_folder_path", weight=0.2),
            BinaryCritic(critic_field="filter_by_category", weight=0.2),
            BinaryCritic(critic_field="limit", weight=0.2),
            BinaryCritic(critic_field="cursor", weight=0.2),
        ],
    )

    return suite
