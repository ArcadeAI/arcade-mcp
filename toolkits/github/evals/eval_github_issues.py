from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_github
from arcade_github.tools.issues import (
    create_issue,
    create_issue_comment,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.9,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
# Register the GitHub tools
catalog.add_module(arcade_github)


@tool_eval()
def github_issues_eval_suite() -> EvalSuite:
    """Evaluation suite for GitHub Issues tools."""
    suite = EvalSuite(
        name="GitHub Issues Tools Evaluation Suite",
        system_message="You are an AI assistant that helps users interact with GitHub issues using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # Create Issue
    suite.add_case(
        name="Create a new issue",
        user_message="Create a new issue in the 'ArcadeAI/arcade-ai' repository with the title 'Bug: Login not working' and description 'Users are unable to log in to the application.' Assign the issue to TestUser, add it to milestone 1, and add the labels 'bug', and 'critical'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "owner": "ArcadeAI",
                    "repo": "arcade-ai",
                    "title": "Bug: Login not working",
                    "body": "Users are unable to log in to the application.",
                    "assignees": ["TestUser"],
                    "milestone": 1,
                    "labels": ["bug", "critical"],
                    "include_extra_data": False,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.2),
            BinaryCritic(critic_field="repo", weight=0.2),
            SimilarityCritic(critic_field="title", weight=0.2),
            SimilarityCritic(critic_field="body", weight=0.1),
            BinaryCritic(critic_field="assignees", weight=0.1),
            BinaryCritic(critic_field="milestone", weight=0.1),
            BinaryCritic(critic_field="labels", weight=0.1),
        ],
    )

    # Create Issue Comment
    suite.add_case(
        name="Add a comment to an existing issue",
        user_message="Add a comment to issue #42 in the 'ArcadeAI/test' repository saying 'This issue is being investigated by the dev team.'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue_comment,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "issue_number": 42,
                    "body": "This issue is being investigated by the dev team.",
                    "include_extra_data": False,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="owner", weight=0.2),
            SimilarityCritic(critic_field="repo", weight=0.2),
            BinaryCritic(critic_field="issue_number", weight=0.3),
            SimilarityCritic(critic_field="body", weight=0.2),
        ],
    )

    return suite
