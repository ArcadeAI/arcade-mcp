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
from arcade_dropbox.tools.files import download_file

rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)


catalog = ToolCatalog()
catalog.add_module(arcade_dropbox)


@tool_eval()
def download_file_eval_suite() -> EvalSuite:
    """Create an evaluation suite for the download_file tool."""
    suite = EvalSuite(
        name="download_file",
        system_message="You are an AI assistant that can interact with files and folders in Dropbox using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Download file in the root folder by file path",
        user_message="Download the file test.txt from Dropbox",
        expected_tool_calls=[
            ExpectedToolCall(
                func=download_file,
                args={
                    "file_path": "test.txt",
                    "file_id": None,
                },
            ),
        ],
        critics=[
            DropboxPathCritic(critic_field="file_path", weight=0.5),
            BinaryCritic(critic_field="file_id", weight=0.5),
        ],
    )

    suite.add_case(
        name="Download file with a sub-folder structure",
        user_message="Download the file Q1report.ppt in the folder AcmeInc/Reports from Dropbox",
        expected_tool_calls=[
            ExpectedToolCall(
                func=download_file,
                args={
                    "file_path": "/AcmeInc/Reports/Q1report.ppt",
                    "file_id": None,
                },
            ),
        ],
        critics=[
            DropboxPathCritic(critic_field="file_path", weight=0.5),
            BinaryCritic(critic_field="file_id", weight=0.5),
        ],
    )

    suite.add_case(
        name="Download file by ID",
        user_message="Download the file id:a4ayc_80_OEAAAAAAAAAYa from Dropbox",
        expected_tool_calls=[
            ExpectedToolCall(
                func=download_file,
                args={
                    "file_path": None,
                    "file_id": "id:a4ayc_80_OEAAAAAAAAAYa",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="file_path", weight=0.5),
            BinaryCritic(critic_field="file_id", weight=0.5),
        ],
    )

    return suite
