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
from arcade_github.tools.models import (
    DiffSide,
    ReviewCommentSubjectType,
    SortDirection,
)
from arcade_github.tools.pull_requests import (
    create_reply_for_review_comment,
    create_review_comment,
    get_pull_request,
    list_pull_request_commits,
    list_pull_requests,
    list_review_comments_on_pull_request,
    update_pull_request,
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
def github_pull_requests_eval_suite() -> EvalSuite:
    """Evaluation suite for GitHub Pull Requests tools."""
    suite = EvalSuite(
        name="GitHub Pull Requests Tools Evaluation Suite",
        system_message="You are an AI assistant that helps users interact with GitHub pull requests using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # List Pull Requests
    suite.add_case(
        name="List all open pull requests",
        user_message="List all open pull requests in the test repository under the ArcadeAI account that are proposing to merge into main.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_pull_requests,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "state": "open",
                    "base": "main",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.2),
            BinaryCritic(critic_field="repo", weight=0.2),
            BinaryCritic(critic_field="state", weight=0.2),
            BinaryCritic(critic_field="base", weight=0.1),
        ],
    )

    # Get Pull Request
    suite.add_case(
        name="Get details of a pull request",
        user_message="Get diff of pull request #72 in the 'ArcadeAI/test' repository. Include all the data that is available in your response.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_pull_request,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "pull_number": 72,
                    "include_diff_content": True,
                    "include_extra_data": True,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.2),
            BinaryCritic(critic_field="repo", weight=0.2),
            BinaryCritic(critic_field="pull_number", weight=0.3),
            BinaryCritic(critic_field="include_extra_data", weight=0.1),
            BinaryCritic(critic_field="include_diff_content", weight=0.2),
        ],
    )

    # Update Pull Request
    suite.add_case(
        name="Update a pull request",
        user_message="Update the title of pull request #72 in the 'ArcadeAI/test' repository to 'Updated Title'.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_pull_request,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "pull_number": 72,
                    "title": "Updated Title",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.2),
            BinaryCritic(critic_field="repo", weight=0.2),
            BinaryCritic(critic_field="pull_number", weight=0.3),
            BinaryCritic(critic_field="title", weight=0.3),
        ],
    )

    # List Pull Request Commits
    suite.add_case(
        name="List commits on a pull request",
        user_message="List all commits for PR 72 in the test repository under ArcadeAI.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_pull_request_commits,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "pull_number": 72,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.2),
            BinaryCritic(critic_field="repo", weight=0.2),
            BinaryCritic(critic_field="pull_number", weight=0.3),
        ],
    )

    # Create Reply for Review Comment
    suite.add_case(
        name="Create a reply to a review comment",
        user_message="Create a reply to the review comment 1778019974 in 'ArcadeAI/test' for pr 72 saying 'Thanks for the suggestion.'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_reply_for_review_comment,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "pull_number": 72,
                    "comment_id": 1778019974,
                    "body": "Thanks for the suggestion.",
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.2),
            BinaryCritic(critic_field="repo", weight=0.2),
            BinaryCritic(critic_field="pull_number", weight=0.2),
            BinaryCritic(critic_field="comment_id", weight=0.2),
            SimilarityCritic(critic_field="body", weight=0.2),
        ],
    )

    # List Review Comments on Pull Request
    suite.add_case(
        name="List all review comments on a pull request",
        user_message="List review comments for pr 72 in the ArcadeAI/test repo. Sort by updated time in ascending order.",
        expected_tool_calls=[
            ExpectedToolCall(
                func=list_review_comments_on_pull_request,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "pull_number": 72,
                    "sort": "updated",
                    "direction": SortDirection.ASC,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.2),
            BinaryCritic(critic_field="repo", weight=0.2),
            BinaryCritic(critic_field="pull_number", weight=0.2),
            BinaryCritic(critic_field="sort", weight=0.2),
            BinaryCritic(critic_field="direction", weight=0.2),
        ],
    )

    # Create Review Comment
    suite.add_case(
        name="Create a review comment on a pull request file",
        user_message="Create a review comment on pr 72 in the 'ArcadeAI/test' repo. The comment should be on the file 'README.md' and says 'nit: you misspelled the word 'intelligence'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_review_comment,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "pull_number": 72,
                    "body": "nit: you misspelled the word 'intelligence'",
                    "path": "README.md",
                    "subject_type": ReviewCommentSubjectType.FILE,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.15),
            BinaryCritic(critic_field="repo", weight=0.15),
            BinaryCritic(critic_field="pull_number", weight=0.2),
            SimilarityCritic(critic_field="body", weight=0.1),
            BinaryCritic(critic_field="path", weight=0.2),
            BinaryCritic(critic_field="subject_type", weight=0.2),
        ],
    )

    # Create Review Comment with Line Numbers
    suite.add_case(
        name="Create a review comment on specific lines of a pull request",
        user_message="Create a review comment on pull request #72 in the 'ArcadeAI/test' repository. The comment should be on the file 'src/main.py', lines 10-15, and say 'Move these to constants.py.'",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_review_comment,
                args={
                    "owner": "ArcadeAI",
                    "repo": "test",
                    "pull_number": 72,
                    "body": "Move these to constants.py.",
                    "path": "src/main.py",
                    "start_line": 10,
                    "end_line": 15,
                    "side": DiffSide.RIGHT,
                    "subject_type": ReviewCommentSubjectType.LINE,
                },
            )
        ],
        critics=[
            BinaryCritic(critic_field="owner", weight=0.1),
            BinaryCritic(critic_field="repo", weight=0.1),
            BinaryCritic(critic_field="pull_number", weight=0.15),
            SimilarityCritic(critic_field="body", weight=0.15),
            BinaryCritic(critic_field="path", weight=0.1),
            BinaryCritic(critic_field="start_line", weight=0.1),
            BinaryCritic(critic_field="end_line", weight=0.1),
            BinaryCritic(critic_field="side", weight=0.1),
            BinaryCritic(critic_field="subject_type", weight=0.1),
        ],
    )

    return suite
