from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_google_drive
from arcade_google_drive.tools import (
    get_file_tree_structure,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_google_drive)


@tool_eval()
def get_file_tree_structure_eval_suite() -> EvalSuite:
    """Create an evaluation suite for Google Drive tools."""
    suite = EvalSuite(
        name="Google Drive Tools Evaluation",
        system_message="You are an AI assistant that can manage Google Drive documents using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    suite.add_case(
        name="get my google drive's file tree structure including shared drives",
        user_message="get my google drive's file tree structure including shared drives",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": True,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
    )

    suite.add_case(
        name="get my google drive's file tree structure without shared drives",
        user_message="get my google drive's file tree structure without shared drives",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": False,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
    )

    suite.add_case(
        name="what are the files in the folder 'hello world' in my google drive?",
        user_message="what are the files in the folder 'hello world' in my google drive?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": False,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
    )

    suite.add_case(
        name="how many files are there in all my google drives, including shared ones?",
        user_message="how many files are there in all my google drives, including shared ones?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_file_tree_structure,
                args={
                    "restrict_to_shared_drive_id": None,
                    "include_shared_drives": True,
                    "include_organization_domain_documents": False,
                    "order_by": None,
                    "limit": None,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="include_shared_drives", weight=0.5),
            BinaryCritic(critic_field="restrict_to_shared_drive_id", weight=0.5 / 4),
            BinaryCritic(critic_field="include_organization_domain_documents", weight=0.5 / 4),
            BinaryCritic(critic_field="order_by", weight=0.5 / 4),
            BinaryCritic(critic_field="limit", weight=0.5 / 4),
        ],
    )

    return suite
