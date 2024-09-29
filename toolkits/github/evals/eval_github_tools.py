import arcade_github
from arcade_github.tools.pull_requests import (
    get_pull_request,
    list_pull_request_commits,
    list_pull_requests,
    update_pull_request,
)
from arcade_github.tools.repositories import (
    get_repository,
)

from arcade.core.catalog import ToolCatalog
from arcade.sdk.eval import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    SimilarityCritic,
    tool_eval,
)
from arcade.sdk.eval.critic import NumericCritic

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.8,
    warn_threshold=0.9,
)

catalog = ToolCatalog()
# Register the GitHub tools
catalog.add_module(arcade_github)


@tool_eval()
def github_eval_suite() -> EvalSuite:
    """Evaluation suite for GitHub tools."""
    suite = EvalSuite(
        name="GitHub Tools Evaluation Suite",
        system_message="You are an AI assistant that helps users interact with GitHub repositories using the provided tools.",
        catalog=catalog,
        rubric=rubric,
    )

    # Pull Requests Tools Evaluation Cases
    ## List Pull Requests
    suite.add_case(
        name="List open pull requests",
        user_message="Show me all open pull requests in the 'ArcadeAI/arcade-ai' repository.",
        expected_tool_calls=[
            (
                list_pull_requests,
                {
                    "owner": "ArcadeAI",
                    "repo": "arcade-ai",
                    "state": "open",
                    "base": "main",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="owner", weight=0.25),
            SimilarityCritic(critic_field="repo", weight=0.25),
            BinaryCritic(critic_field="state", weight=0.25),
            BinaryCritic(critic_field="base", weight=0.25),
        ],
    )

    suite.add_case(
        name="List closed pull requests with specific base branch",
        user_message="List all closed pull requests in 'octocat/Hello-World' that were merged into 'develop' branch.",
        expected_tool_calls=[
            (
                list_pull_requests,
                {
                    "owner": "octocat",
                    "repo": "Hello-World",
                    "state": "closed",
                    "base": "develop",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="owner", weight=0.25),
            SimilarityCritic(critic_field="repo", weight=0.25),
            BinaryCritic(critic_field="state", weight=0.25),
            SimilarityCritic(critic_field="base", weight=0.25),
        ],
    )

    ## Get Pull Request
    suite.add_case(
        name="Get specific pull request details",
        user_message="Get details of pull request number 101 in 'ArcadeAI/arcade-ai'.",
        expected_tool_calls=[
            (
                get_pull_request,
                {
                    "owner": "ArcadeAI",
                    "repo": "arcade-ai",
                    "pull_number": 101,
                    "include_extra_data": False,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="owner", weight=0.25),
            SimilarityCritic(critic_field="repo", weight=0.25),
            NumericCritic(critic_field="pull_number", weight=0.5, value_range=(1, 10000)),
        ],
    )

    ## Update Pull Request
    suite.add_case(
        name="Update pull request title",
        user_message="Change the title of pull request #42 in 'octocat/Hello-World' to 'Updated PR Title'.",
        expected_tool_calls=[
            (
                update_pull_request,
                {
                    "owner": "octocat",
                    "repo": "Hello-World",
                    "pull_number": 42,
                    "title": "Updated PR Title",
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="owner", weight=0.2),
            SimilarityCritic(critic_field="repo", weight=0.2),
            NumericCritic(critic_field="pull_number", weight=0.2, value_range=(1, 10000)),
            SimilarityCritic(critic_field="title", weight=0.4),
        ],
    )

    ## List Pull Request Commits
    suite.add_case(
        name="List commits in a pull request",
        user_message="What are the commits in pull request #10 in 'ArcadeAI/arcade-ai'?",
        expected_tool_calls=[
            (
                list_pull_request_commits,
                {
                    "owner": "ArcadeAI",
                    "repo": "arcade-ai",
                    "pull_number": 10,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="owner", weight=0.3),
            SimilarityCritic(critic_field="repo", weight=0.3),
            NumericCritic(critic_field="pull_number", weight=0.4, value_range=(1, 10000)),
        ],
    )

    # Repositories Tools Evaluation Cases

    ## Get Repository Details
    suite.add_case(
        name="Get repository details",
        user_message="Get details of the 'arcade-ai' repository owned by 'ArcadeAI'.",
        expected_tool_calls=[
            (
                get_repository,
                {
                    "owner": "ArcadeAI",
                    "repo": "arcade-ai",
                    "include_extra_data": False,
                },
            )
        ],
        critics=[
            SimilarityCritic(critic_field="owner", weight=0.4),
            SimilarityCritic(critic_field="repo", weight=0.4),
            BinaryCritic(critic_field="include_extra_data", weight=0.2),
        ],
    )

    return suite
