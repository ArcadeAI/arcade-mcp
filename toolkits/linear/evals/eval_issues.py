"""
Comprehensive evaluation suite for Linear issue management tools.
"""

from arcade_evals import (
    BinaryCritic,
    EvalRubric,
    EvalSuite,
    ExpectedToolCall,
    SimilarityCritic,
    tool_eval,
)
from arcade_tdk import ToolCatalog

import arcade_linear
from arcade_linear.tools.issues import (
    add_comment_to_issue,
    create_issue,
    get_issue,
    get_templates,
    search_issues,
    update_issue,
)

# Evaluation rubric
rubric = EvalRubric(
    fail_threshold=0.85,
    warn_threshold=0.95,
)

catalog = ToolCatalog()
catalog.add_module(arcade_linear)


@tool_eval()
def search_issues_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for search_issues tool"""
    suite = EvalSuite(
        name="Search Issues Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user find and manage Linear issues."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Find all high-priority bugs assigned to me
    suite.add_case(
        name="Search high-priority bugs assigned to me",
        user_message="Find all high-priority bugs assigned to me",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "priority": "high",
                    "assignee": "me",
                    "labels": ["bug"],
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="priority", weight=0.4),
            BinaryCritic(critic_field="assignee", weight=0.4),
            SimilarityCritic(critic_field="labels", weight=0.2),
        ],
    )

    # Eval Prompt: Show me all "In Progress" issues in the Arcade team from the last 2 weeks
    suite.add_case(
        name="Find in-progress Arcade issues from last 2 weeks",
        user_message="Show me all \"In Progress\" issues in the Arcade team from the last 2 weeks",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "status": "In Progress",
                    "team": "Arcade",
                    "created_after": "last 2 weeks",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="status", weight=0.4),
            BinaryCritic(critic_field="team", weight=0.3),
            SimilarityCritic(critic_field="created_after", weight=0.3),
        ],
    )

    # Eval Prompt: Show me all issues in the "arcade testing" project
    suite.add_case(
        name="Find issues in arcade testing project",
        user_message="Show me all issues in the \"arcade testing\" project",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "project": "arcade testing",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="project", weight=1.0),
        ],
    )

    # Eval Prompt: Find urgent issues created by Shub in the last month
    suite.add_case(
        name="Find urgent issues created by Shub",
        user_message="Find urgent issues created by Shub in the last month",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "priority": "urgent",
                    "creator": "Shub",
                    "created_after": "last month",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="priority", weight=0.4),
            BinaryCritic(critic_field="creator", weight=0.3),
            SimilarityCritic(critic_field="created_after", weight=0.3),
        ],
    )

    # Eval Prompt: Show all issues resolved in the last week by the test team
    suite.add_case(
        name="Find recently resolved issues by test team",
        user_message="Show all issues resolved in the last week by the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "status": "Done",
                    "team": "test",
                    "updated_after": "last week",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="status", weight=0.4),
            BinaryCritic(critic_field="team", weight=0.3),
            SimilarityCritic(critic_field="updated_after", weight=0.3),
        ],
    )

    # Eval Prompt: Find issues containing "authentication" that are unassigned
    suite.add_case(
        name="Find unassigned authentication issues",
        user_message="Find issues containing \"authentication\" that are unassigned",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "keywords": "authentication",
                    "assignee": "unassigned",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="keywords", weight=0.5),
            BinaryCritic(critic_field="assignee", weight=0.5),
        ],
    )

    # Eval Prompt: Find all bugs marked as "critical" in the test team
    suite.add_case(
        name="Search for critical bugs in test team",
        user_message="Find all bugs marked as \"critical\" in the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "labels": ["critical", "bug"],
                    "team": "test",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="labels", weight=0.6),
            BinaryCritic(critic_field="team", weight=0.4),
        ],
    )

    # Eval Prompt: List unassigned tasks in the Arcade team created in the past 2 weeks
    suite.add_case(
        name="Find unassigned recent tasks in Arcade team",
        user_message="List unassigned tasks in the Arcade team created in the past 2 weeks",
        expected_tool_calls=[
            ExpectedToolCall(
                func=search_issues,
                args={
                    "assignee": "unassigned",
                    "team": "Arcade",
                    "created_after": "past 2 weeks",
                    "labels": ["task"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="assignee", weight=0.3),
            BinaryCritic(critic_field="team", weight=0.3),
            SimilarityCritic(critic_field="created_after", weight=0.2),
            SimilarityCritic(critic_field="labels", weight=0.2),
        ],
    )

    return suite


@tool_eval()
def get_issue_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for get_issue tool"""
    suite = EvalSuite(
        name="Get Issue Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user get detailed information about Linear issues."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Show me complete details for issue API-789
    suite.add_case(
        name="Get complete issue details",
        user_message="Show me complete details for issue API-789",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue,
                args={
                    "issue_id": "API-789",
                    "include_comments": True,
                    "include_attachments": True,
                    "include_relations": True,
                    "include_children": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.6),
            BinaryCritic(critic_field="include_comments", weight=0.1),
            BinaryCritic(critic_field="include_attachments", weight=0.1),
            BinaryCritic(critic_field="include_relations", weight=0.1),
            BinaryCritic(critic_field="include_children", weight=0.1),
        ],
    )

    # Eval Prompt: Find all dependencies for issue PROJ-100
    suite.add_case(
        name="Get issue dependencies",
        user_message="Find all dependencies for issue PROJ-100",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue,
                args={
                    "issue_id": "PROJ-100",
                    "include_relations": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.7),
            BinaryCritic(critic_field="include_relations", weight=0.3),
        ],
    )

    # Eval Prompt: Get issue FE-123 with all related sub-issues and dependencies
    suite.add_case(
        name="Get issue with sub-issues and dependencies",
        user_message="Get issue FE-123 with all related sub-issues and dependencies",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_issue,
                args={
                    "issue_id": "FE-123",
                    "include_relations": True,
                    "include_children": True,
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            BinaryCritic(critic_field="include_relations", weight=0.25),
            BinaryCritic(critic_field="include_children", weight=0.25),
        ],
    )

    return suite


@tool_eval()
def update_issue_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for update_issue tool"""
    suite = EvalSuite(
        name="Update Issue Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user update Linear issues."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Move issue TES-8 to "Done" status
    suite.add_case(
        name="Update issue status to Done",
        user_message="Move issue TES-8 to \"Done\" status",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue_id": "TES-8",
                    "status": "Done",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            BinaryCritic(critic_field="status", weight=0.5),
        ],
    )

    # Eval Prompt: Update issue description with latest findings and change status to "In Review"
    suite.add_case(
        name="Update description and status",
        user_message="Update issue TES-8 description with latest findings and change status to \"In Review\"",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue_id": "TES-8",
                    "description": "latest findings",
                    "status": "In Review",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.4),
            SimilarityCritic(critic_field="description", weight=0.3),
            BinaryCritic(critic_field="status", weight=0.3),
        ],
    )

    # Eval Prompt: Update issue API-789 to add the "customer request" label
    suite.add_case(
        name="Add customer request label to issue",
        user_message="Update issue API-789 to add the \"customer request\" label to it",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue_id": "API-789",
                    "labels": ["customer request"],
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            BinaryCritic(critic_field="labels", weight=0.5),
        ],
    )

    # Eval Prompt: Update issue HELP-123 to assign it to shub and set priority to urgent
    suite.add_case(
        name="Assign issue and set urgent priority",
        user_message="Update issue HELP-123 to assign it to shub and set priority to urgent",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue_id": "HELP-123",
                    "assignee": "shub",
                    "priority": "urgent",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.4),
            BinaryCritic(critic_field="assignee", weight=0.3),
            BinaryCritic(critic_field="priority", weight=0.3),
        ],
    )

    # Eval Prompt: Update issue BE-456 to set priority to high and add to current cycle
    suite.add_case(
        name="Set high priority and add to sprint",
        user_message="Update issue BE-456 to set priority to high and add to current cycle",
        expected_tool_calls=[
            ExpectedToolCall(
                func=update_issue,
                args={
                    "issue_id": "BE-456",
                    "priority": "high",
                    "cycle": "current",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.4),
            BinaryCritic(critic_field="priority", weight=0.3),
            BinaryCritic(critic_field="cycle", weight=0.3),
        ],
    )

    return suite


@tool_eval()
def create_issue_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for create_issue tool"""
    suite = EvalSuite(
        name="Create Issue Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user create Linear issues."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Create a critical bug report for the checkout process in the E-commerce team
    suite.add_case(
        name="Create critical checkout bug for E-commerce team",
        user_message="Create a critical bug report for the checkout process in the E-commerce team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "checkout process",
                    "team": "E-commerce",
                    "priority": "urgent",
                    "labels": ["bug", "critical"],
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="title", weight=0.4),
            BinaryCritic(critic_field="team", weight=0.3),
            SimilarityCritic(critic_field="priority", weight=0.2),
            SimilarityCritic(critic_field="labels", weight=0.1),
        ],
    )

    # Eval Prompt: Add a feature request for dark mode to the UI team backlog
    suite.add_case(
        name="Create dark mode feature request",
        user_message="Add a feature request for dark mode to the UI team backlog",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "dark mode",
                    "team": "UI",
                    "labels": ["feature"],
                    "status": "Backlog",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="title", weight=0.4),
            BinaryCritic(critic_field="team", weight=0.3),
            SimilarityCritic(critic_field="labels", weight=0.2),
            SimilarityCritic(critic_field="status", weight=0.1),
        ],
    )

    # Eval Prompt: Create a sub-issue under PROJ-100 for database migration testing
    suite.add_case(
        name="Create sub-issue for database migration",
        user_message="Create a sub-issue under PROJ-100 for database migration testing",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "database migration testing",
                    "parent_issue": "PROJ-100",
                    "team": "Backend",
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="title", weight=0.5),
            BinaryCritic(critic_field="parent_issue", weight=0.3),
            SimilarityCritic(critic_field="team", weight=0.2),
        ],
    )

    # Eval Prompt: Log a security vulnerability with high priority and assign to the Security team
    suite.add_case(
        name="Create security vulnerability issue",
        user_message="Log a security vulnerability with high priority and assign to the Security team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "security vulnerability",
                    "priority": "high",
                    "team": "Security",
                    "labels": ["security", "vulnerability"],
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="title", weight=0.4),
            SimilarityCritic(critic_field="priority", weight=0.3),
            BinaryCritic(critic_field="team", weight=0.2),
            SimilarityCritic(critic_field="labels", weight=0.1),
        ],
    )

    # Eval Prompt: Create issue with auto-created labels
    suite.add_case(
        name="Create issue with new labels",
        user_message="Create a task for API optimization with labels: performance, backend, optimization",
        expected_tool_calls=[
            ExpectedToolCall(
                func=create_issue,
                args={
                    "title": "API optimization",
                    "team": "Backend",
                    "labels": ["performance", "backend", "optimization"],
                },
            ),
        ],
        critics=[
            SimilarityCritic(critic_field="title", weight=0.5),
            SimilarityCritic(critic_field="team", weight=0.3),
            BinaryCritic(critic_field="labels", weight=0.2),
        ],
    )

    return suite


@tool_eval()
def add_comment_to_issue_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for add_comment_to_issue tool"""
    suite = EvalSuite(
        name="Add Comment to Issue Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user add comments to Linear issues for documentation and communication."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Create a comment on issue API-789 explaining the fix
    suite.add_case(
        name="Add explanation comment to issue",
        user_message="Create a comment on issue API-789 explaining the fix",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "API-789",
                    "comment": "explaining the fix",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.6),
            SimilarityCritic(critic_field="comment", weight=0.4),
        ],
    )

    # Eval Prompt: Comment on TES-8 that testing is complete and ready for review
    suite.add_case(
        name="Add testing completion comment",
        user_message="Comment on TES-8 that testing is complete and ready for review",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "TES-8",
                    "comment": "testing is complete and ready for review",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            SimilarityCritic(critic_field="comment", weight=0.5),
        ],
    )

    # Eval Prompt: Add a status update comment to PROJ-100
    suite.add_case(
        name="Add status update comment",
        user_message="Add a status update comment to PROJ-100",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "PROJ-100",
                    "comment": "status update",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.6),
            SimilarityCritic(critic_field="comment", weight=0.4),
        ],
    )

    # Eval Prompt: Create a comment on FE-123 with reproduction steps
    suite.add_case(
        name="Add reproduction steps comment",
        user_message="Create a comment on FE-123 with reproduction steps",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "FE-123",
                    "comment": "reproduction steps",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.8),
            SimilarityCritic(critic_field="comment", weight=0.2),
        ],
    )

    # Eval Prompt: Create a detailed progress comment on BE-456 about the implementation
    suite.add_case(
        name="Add detailed progress comment",
        user_message="Create a detailed progress comment on BE-456 about the implementation",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "BE-456",
                    "comment": "detailed progress comment about the implementation",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            SimilarityCritic(critic_field="comment", weight=0.5),
        ],
    )

    # Eval Prompt: Comment on UI-789 that the design needs approval before proceeding
    suite.add_case(
        name="Add approval request comment",
        user_message="Comment on UI-789 that the design needs approval before proceeding",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "UI-789",
                    "comment": "the design needs approval before proceeding",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            SimilarityCritic(critic_field="comment", weight=0.5),
        ],
    )

    # Eval Prompt: Create a comment on QA-123 with test results and findings
    suite.add_case(
        name="Add test results comment",
        user_message="Create a comment on QA-123 with test results and findings",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "QA-123",
                    "comment": "test results and findings",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.8),
            SimilarityCritic(critic_field="comment", weight=0.2),
        ],
    )

    # Eval Prompt: Comment on DOCS-456 that documentation has been updated
    suite.add_case(
        name="Add documentation update comment",
        user_message="Comment on DOCS-456 that documentation has been updated",
        expected_tool_calls=[
            ExpectedToolCall(
                func=add_comment_to_issue,
                args={
                    "issue_id": "DOCS-456",
                    "comment": "documentation has been updated",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="issue_id", weight=0.5),
            SimilarityCritic(critic_field="comment", weight=0.5),
        ],
    )

    return suite


@tool_eval()
def get_templates_eval_suite() -> EvalSuite:
    """Comprehensive evaluation suite for get_templates tool"""
    suite = EvalSuite(
        name="Get Templates Evaluation",
        system_message=(
            "You are an AI assistant with access to Linear tools. "
            "Use them to help the user get available issue templates for structured issue creation."
        ),
        catalog=catalog,
        rubric=rubric,
    )

    # Eval Prompt: Show me all available issue templates
    suite.add_case(
        name="Get all available templates",
        user_message="Show me all available issue templates",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={},
            ),
        ],
        critics=[],  # No specific args expected
    )

    # Eval Prompt: What templates are available for the Frontend team?
    suite.add_case(
        name="Get Frontend team templates",
        user_message="What templates are available for the Frontend team?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={
                    "team": "Frontend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: List issue templates for the Backend team
    suite.add_case(
        name="Get Backend team templates",
        user_message="List issue templates for the Backend team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={
                    "team": "Backend",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Show me all available templates
    suite.add_case(
        name="Get bug report templates",
        user_message="Show me all available templates",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={},
            ),
        ],
        critics=[],  # No specific args expected
    )

    # Eval Prompt: What templates does the Product team have?
    suite.add_case(
        name="Get Product team templates",
        user_message="What templates does the Product team have?",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={
                    "team": "Product",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: List templates for the test team
    suite.add_case(
        name="Get test team templates",
        user_message="List templates for the test team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={
                    "team": "test",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    # Eval Prompt: Show me templates for all teams
    suite.add_case(
        name="Get feature request templates",
        user_message="Show me templates for all teams",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={},
            ),
        ],
        critics=[],  # No specific args expected
    )

    # Eval Prompt: Get templates available for the Design team
    suite.add_case(
        name="Get Design team templates",
        user_message="Get templates available for the Design team",
        expected_tool_calls=[
            ExpectedToolCall(
                func=get_templates,
                args={
                    "team": "Design",
                },
            ),
        ],
        critics=[
            BinaryCritic(critic_field="team", weight=1.0),
        ],
    )

    return suite 