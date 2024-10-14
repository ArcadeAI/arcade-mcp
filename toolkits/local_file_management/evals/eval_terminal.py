import arcade_local_file_management
from arcade_local_file_management.tools.terminal import (
    copy_file,
    copy_folder,
    create_directory,
    create_file,
    get_text_file_details,
    list_directory,
    move_file,
    move_folder,
    remove_file,
    rename_file,
    rename_folder,
    search_file,
)

from arcade.core.catalog import ToolCatalog
from arcade.sdk.eval import (
    EvalRubric,
    EvalSuite,
    SimilarityCritic,
    tool_eval,
)
from arcade.sdk.eval.critic import BinaryCritic

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)


catalog = ToolCatalog()
catalog.add_module(arcade_local_file_management)


@tool_eval()
def text_eval_suite():
    suite = EvalSuite(
        name="Local Tools Evaluation",
        system_message="You are an AI assistant with access to tools that can manipulate the user's local machine. Use them to help the user with their tasks.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="Get file details",
        user_message="what's /Users/johndoe/Desktop/hello.py implementing?",
        expected_tool_calls=[
            (
                get_text_file_details,
                {
                    "file_path": "/Users/johndoe/Desktop/hello.py",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="file_path", weight=0.5),
        ],
    )

    suite.add_case(
        name="Search file content",
        user_message='Search /Users/johndoe/Desktop/hello.py for all instances of critic_field=".*"',
        expected_tool_calls=[
            (
                search_file,
                {
                    "file_path": "/Users/johndoe/Desktop/hello.py",
                    "pattern": 'critic_field=".*"',
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="file_path", weight=0.5),
        ],
    )

    suite.add_case(
        name="List directory contents",
        user_message="Which files are in the same folder as /Users/johndoe/Desktop/foobar.md??????",
        expected_tool_calls=[
            (
                list_directory,
                {
                    "file_path": "/Users/johndoe/Desktop/",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="file_path", weight=1.0),
        ],
    )

    suite.add_case(
        name="Create file with content",
        user_message="Create a file in the /Users/johndoe/Desktop dir called hello.py that prints Hello world to the console.",
        expected_tool_calls=[
            (
                create_file,
                {
                    "file_path": "/Users/johndoe/Desktop/hello.py",
                    "contents": "print('Hello world')",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="file_path", weight=0.7),
            SimilarityCritic(critic_field="contents", weight=0.3),
        ],
    )

    suite.add_case(
        name="Create deep nested directory",
        user_message="Create a folder located at /Users/foo/bar/baz/foo/bar/baz/foo/foo/foo/bar/baz/foo/baz/bar/foo/baz/baz/baz/",
        expected_tool_calls=[
            (
                create_directory,
                {
                    "directory_path": "/Users/foo/bar/baz/foo/bar/baz/foo/foo/foo/bar/baz/foo/baz/bar/foo/baz/baz/baz/",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="file_path", weight=1.0),
        ],
    )

    expected_create_file_calls = [
        (
            create_file,
            {"file_path": f"/Users/foo/bar/{i}.txt", "contents": f"This is the {i} file"},
        )
        for i in range(1, 11)
    ]

    suite.add_case(
        name="Create directory and multiple files",
        user_message="Create a folder located at /Users/foo/bar/baz and then after you create the directory, I want you to create 10 files named 1.txt, 2.txt, ..., 10.txt in the /Users/foo/bar folder. For each of these files have the content be 'This is the X file'",
        expected_tool_calls=[
            (
                create_directory,
                {
                    "directory_path": "/Users/foo/bar/baz",
                },
            ),
            *expected_create_file_calls,
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="directory_path", weight=0.3),
            BinaryCritic(critic_field="file_path", weight=0.4),
            SimilarityCritic(critic_field="contents", weight=0.3),
        ],
    )

    suite.add_case(
        name="Remove file",
        user_message="Remove the old_file.txt file from Desktop directory. This is for the johndoe user e.g. /Users/johndoe.",
        expected_tool_calls=[
            (
                remove_file,
                {
                    "file_path": "/Users/johndoe/Desktop/old_file.txt",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="file_path", weight=1.0),
        ],
    )

    suite.add_case(
        name="Copy file",
        user_message="Copy /Users/johndoe/Documents/important.txt into a new file /Users/johndoe/Backup/important_backup.txt",
        expected_tool_calls=[
            (
                copy_file,
                {
                    "source_path": "/Users/johndoe/Documents/important.txt",
                    "destination_path": "/Users/johndoe/Backup/important_backup.txt",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="source_path", weight=0.5),
            BinaryCritic(critic_field="destination_path", weight=0.5),
        ],
    )

    suite.add_case(
        name="Move file",
        user_message="Move the file /Users/johndoe/Downloads/temp.txt to /Users/johndoe/Documents/final.txt",
        expected_tool_calls=[
            (
                move_file,
                {
                    "source_path": "/Users/johndoe/Downloads/temp.txt",
                    "destination_path": "/Users/johndoe/Documents/final.txt",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="source_path", weight=0.5),
            BinaryCritic(critic_field="destination_path", weight=0.5),
        ],
    )

    suite.add_case(
        name="Rename file",
        user_message="Rename the file /Users/johndoe/Documents/old_report.txt to new_report.txt",
        expected_tool_calls=[
            (
                rename_file,
                {
                    "file_path": "/Users/johndoe/Documents/old_report.txt",
                    "new_name": "new_report.txt",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="file_path", weight=0.5),
            BinaryCritic(critic_field="new_name", weight=0.5),
        ],
    )

    suite.add_case(
        name="Copy folder",
        user_message="Whenever I refer to 'Desktop', I am referring to the path /Users/johndoe/Desktop. Copy the folder old_project that is on my desktop to /Users/johndoe/Archives/old_project_backup",
        expected_tool_calls=[
            (
                copy_folder,
                {
                    "source_path": "/Users/johndoe/Desktop/old_project",
                    "destination_path": "/Users/johndoe/Archives/old_project_backup",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="source_path", weight=0.5),
            BinaryCritic(critic_field="destination_path", weight=0.5),
        ],
    )

    suite.add_case(
        name="Move folder",
        user_message="Whenever I refer to 'Desktop', I am referring to the path /Users/johndoe/Desktop. Move the folder old_project that is on my desktop to /Users/johndoe/Archives/old_project_backup",
        expected_tool_calls=[
            (
                move_folder,
                {
                    "source_path": "/Users/johndoe/Desktop/temp_files",
                    "destination_path": "/Users/johndoe/Archives/old_project_backup",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="source_path", weight=0.5),
            BinaryCritic(critic_field="destination_path", weight=0.5),
        ],
    )

    suite.add_case(
        name="Rename folder",
        user_message="Rename the folder /Users/johndoe/Documents/old_project to new_project",
        expected_tool_calls=[
            (
                rename_folder,
                {
                    "folder_path": "/Users/johndoe/Documents/old_project",
                    "new_name": "new_project",
                },
            )
        ],
        rubric=rubric,
        critics=[
            BinaryCritic(critic_field="folder_path", weight=0.5),
            BinaryCritic(critic_field="new_name", weight=0.5),
        ],
    )

    return suite
