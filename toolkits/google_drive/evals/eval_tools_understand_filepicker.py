from arcade_evals import (
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

from arcade_google_drive.tools import (
    get_file_tree_structure,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_tool(get_file_tree_structure, "GoogleDrive")

get_file_tree_structure_history = [
    {"role": "system", "content": "Today is 2025-07-03, Thursday."},
    {"role": "user", "content": "get my file tree structure"},
    {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_EnqRPmIx3zrquDA7PuZ5NtK6",
                "type": "function",
                "function": {"name": "GoogleDrive_GetFileTreeStructure", "arguments": "{}"},
            }
        ],
    },
    {
        "role": "tool",
        "content": '{"drives":[]}',
        "tool_call_id": "call_EnqRPmIx3zrquDA7PuZ5NtK6",
        "name": "GoogleDrive_GetFileTreeStructure",
    },
    {
        "role": "assistant",
        "content": "I could not find any files in your Google Drive. To select and grant access permissions to additional files and folders, use [this Google Drive File Picker link](https://cloud.bosslevel.dev/api/v1/google/drive_picker?config=eyXRoIjogM3NsdnFrMmtqODlldNuLmF0=).",
    },
]


@tool_eval()
def tools_understand_filepicker_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Drive tools."""
    suite = EvalSuite(
        name="Google Drive Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Drive using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Ensure LLM understands that after using file picker, it should call the tool again",
        user_message="ok i followed your suggestion and went to that url. how has it changed?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={},
            )
        ],
        additional_messages=get_file_tree_structure_history,
    )
    return suite
