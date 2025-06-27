"""
Comprehensive unit tests for Linear toolkit fixes.
Tests the specific edge cases and scenarios mentioned in the fix instructions.
"""

from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from arcade_core.errors import ToolExecutionError
from arcade_tdk import ToolContext

from arcade_linear.tools.issues import create_issue, search_issues, update_issue
from arcade_linear.utils import (
    build_issue_filter,
    clean_issue_data,
    resolve_issue_identifier_to_uuid,
    resolve_labels_with_autocreate,
    resolve_projects_by_name,
)


@pytest.fixture
def mock_context():
    """Create a mock ToolContext for testing"""
    context = MagicMock(spec=ToolContext)
    context.get_auth_token_or_empty.return_value = "test-token"
    return context


class TestIssueFilterBuilding:
    """Test the build_issue_filter function with various scenarios"""

    def test_search_query_uses_or_structure(self):
        """Test that search queries use the new OR structure instead of searchableContent"""
        filter_obj = build_issue_filter(search_query="authentication")

        # Should use OR structure for title, description, and label names
        assert "or" in filter_obj
        assert len(filter_obj["or"]) == 3

        # Should contain the three search conditions
        expected_conditions = [
            {"title": {"containsIgnoreCase": "authentication"}},
            {"description": {"containsIgnoreCase": "authentication"}},
            {"labels": {"some": {"name": {"containsIgnoreCase": "authentication"}}}},
        ]

        for condition in expected_conditions:
            assert condition in filter_obj["or"]

        # Should NOT use the old searchableContent field
        assert "searchableContent" not in filter_obj

    def test_unassigned_filter_structure(self):
        """Test that unassigned filtering uses the correct null structure"""
        filter_obj = build_issue_filter(assignee_id="unassigned")

        # Should use null: True for unassigned
        assert filter_obj["assignee"] == {"null": True}

    def test_assigned_filter_structure(self):
        """Test that assigned filtering uses the correct id structure"""
        filter_obj = build_issue_filter(assignee_id="user_123")

        # Should use id: {eq: ...} for specific assignee
        assert filter_obj["assignee"] == {"id": {"eq": "user_123"}}

    def test_combined_filters(self):
        """Test combining multiple filters including search, assignee, team, labels"""
        filter_obj = build_issue_filter(
            search_query="bug",
            assignee_id="unassigned",
            team_id="team_123",
            label_ids=["label_456", "label_789"],
            priority=1,
        )

        # Should have all expected filters
        assert "or" in filter_obj  # Search query
        assert filter_obj["assignee"] == {"null": True}  # Unassigned
        assert filter_obj["team"] == {"id": {"eq": "team_123"}}  # Team
        assert filter_obj["priority"] == {"eq": 1}  # Priority

        # Multiple labels should use AND logic (in 'and' condition)
        assert "and" in filter_obj
        label_conditions = filter_obj["and"]
        assert len(label_conditions) == 2
        assert {"labels": {"some": {"id": {"eq": "label_456"}}}} in label_conditions
        assert {"labels": {"some": {"id": {"eq": "label_789"}}}} in label_conditions

    @pytest.mark.asyncio
    async def test_create_new_labels_when_none_exist(self, mock_context):
        """Test that new labels are created when they don't exist globally"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock empty global labels response
            mock_client.get_labels.return_value = {"nodes": []}

            # Mock successful label creation
            mock_client.create_label.side_effect = [
                {
                    "success": True,
                    "label": {
                        "id": "new_feature_label",
                        "name": "feature",
                        "color": "#10b981",
                        "description": "Auto-created label for feature",
                    },
                },
                {
                    "success": True,
                    "label": {
                        "id": "new_enhancement_label",
                        "name": "enhancement",
                        "color": "#3b82f6",
                        "description": "Auto-created label for enhancement",
                    },
                },
            ]

            # Test creating new labels
            result = await resolve_labels_with_autocreate(
                mock_context, ["feature", "enhancement"], team_id="team_lmao"
            )

            # Should have created both labels
            assert len(result) == 2
            assert result[0]["id"] == "new_feature_label"
            assert result[0]["name"] == "feature"
            assert result[1]["id"] == "new_enhancement_label"
            assert result[1]["name"] == "enhancement"

            # Should have checked globally first
            mock_client.get_labels.assert_called_once_with()

            # Should have created both labels with team scope
            assert mock_client.create_label.call_count == 2
            mock_client.create_label.assert_any_call(
                name="feature",
                team_id="team_lmao",
                color=ANY,  # Color is computed by hash
                description="Auto-created team-specific label for feature",
            )
            mock_client.create_label.assert_any_call(
                name="enhancement",
                team_id="team_lmao",
                color=ANY,  # Color is computed by hash
                description="Auto-created team-specific label for enhancement",
            )

    @pytest.mark.asyncio
    async def test_handle_duplicate_error_gracefully(self, mock_context):
        """Test that duplicate label errors are handled by refetching globally"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # First call: empty labels (race condition setup)
            # Second call: label now exists (after race condition)
            mock_client.get_labels.side_effect = [
                {"nodes": []},  # Initial check finds nothing
                {
                    "nodes": [  # Refetch after duplicate error finds it
                        {
                            "id": "race_condition_label",
                            "name": "bug",
                            "color": "#ef4444",
                            "description": "Created by someone else",
                        }
                    ]
                },
            ]

            # Mock duplicate error on creation
            mock_client.create_label.side_effect = ToolExecutionError(
                "Failed to create label 'bug': duplicate label name"
            )

            # Test handling race condition
            result = await resolve_labels_with_autocreate(
                mock_context, ["bug"], team_id="team_lmao"
            )

            # Should have found the label after refetch
            assert len(result) == 1
            assert result[0]["id"] == "race_condition_label"
            assert result[0]["name"] == "bug"

            # Should have called get_labels twice (initial + refetch)
            assert mock_client.get_labels.call_count == 2

            # Should have tried to create once (before getting duplicate error)
            mock_client.create_label.assert_called_once()

    @pytest.mark.asyncio
    async def test_mixed_existing_and_new_labels(self, mock_context):
        """Test resolving a mix of existing and new labels"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock global labels - "bug" exists, "new-feature" doesn't
            mock_client.get_labels.return_value = {
                "nodes": [
                    {
                        "id": "existing_bug_label",
                        "name": "bug",
                        "color": "#ef4444",
                        "description": "Existing bug label",
                    }
                ]
            }

            # Mock successful creation of new label
            mock_client.create_label.return_value = {
                "success": True,
                "label": {
                    "id": "new_feature_label",
                    "name": "new-feature",
                    "color": "#10b981",
                    "description": "Auto-created label for new-feature",
                },
            }

            # Test mixed scenario
            result = await resolve_labels_with_autocreate(
                mock_context,
                ["bug", "new-feature"],  # One exists, one doesn't
                team_id="team_lmao",
            )

            # Should have reused existing + created new
            assert len(result) == 2
            assert result[0]["id"] == "existing_bug_label"  # Reused
            assert result[0]["name"] == "bug"
            assert result[1]["id"] == "new_feature_label"  # Created
            assert result[1]["name"] == "new-feature"

            # Should have checked globally
            mock_client.get_labels.assert_called_once_with()

            # Should have created only the new label
            mock_client.create_label.assert_called_once_with(
                name="new-feature",
                team_id="team_lmao",
                color=ANY,  # Color is computed by hash
                description="Auto-created team-specific label for new-feature",
            )


class TestTeamSpecificLabelResolution:
    """Test that labels are resolved with proper team-specific behavior"""

    @pytest.mark.asyncio
    async def test_use_team_specific_label_when_available(self, mock_context):
        """Test that team-specific labels are preferred over global ones"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock labels response - same name exists for different teams
            mock_client.get_labels.return_value = {
                "nodes": [
                    {
                        "id": "global_bug_label",
                        "name": "bug",
                        "color": "#ff0000",
                        "team": None,  # Global label
                    },
                    {
                        "id": "other_team_bug_label",
                        "name": "bug",
                        "color": "#00ff00",
                        "team": {
                            "id": "team_other",
                            "key": "OTHER",
                            "name": "Other Team",
                        },
                    },
                    {
                        "id": "lmao_team_bug_label",
                        "name": "bug",
                        "color": "#0000ff",
                        "team": {
                            "id": "team_lmao",
                            "key": "LMAO",
                            "name": "Lmao Team",
                        },
                    },
                ]
            }

            # Test team-specific resolution
            result = await resolve_labels_with_autocreate(
                mock_context, ["bug"], team_id="team_lmao"
            )

            # Should prefer the team-specific label
            assert len(result) == 1
            assert result[0]["id"] == "lmao_team_bug_label"
            assert result[0]["team"]["id"] == "team_lmao"

            # Should NOT try to create any labels
            mock_client.create_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_use_global_label_when_no_team_specific(self, mock_context):
        """Test that global labels are used when no team-specific version exists"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock labels response - only global label exists
            mock_client.get_labels.return_value = {
                "nodes": [
                    {
                        "id": "global_feature_label",
                        "name": "feature",
                        "color": "#00ff00",
                        "team": None,  # Global label (no team)
                    },
                    {
                        "id": "other_team_bug_label",
                        "name": "bug",
                        "color": "#ff0000",
                        "team": {
                            "id": "team_other",
                            "key": "OTHER",
                            "name": "Other Team",
                        },
                    },
                ]
            }

            # Test global label usage
            result = await resolve_labels_with_autocreate(
                mock_context, ["feature"], team_id="team_lmao"
            )

            # Should use the global label
            assert len(result) == 1
            assert result[0]["id"] == "global_feature_label"
            assert result[0]["team"] is None  # Global label

            # Should NOT try to create any labels
            mock_client.create_label.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_team_specific_when_exists_for_other_team(
        self, mock_context
    ):
        """Test that new team-specific labels are created when label exists for other teams only"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock labels response - label exists only for other team
            mock_client.get_labels.return_value = {
                "nodes": [
                    {
                        "id": "other_team_critical_label",
                        "name": "critical",
                        "color": "#ff0000",
                        "team": {
                            "id": "team_other",
                            "key": "OTHER",
                            "name": "Other Team",
                        },
                    }
                ]
            }

            # Mock successful label creation
            mock_client.create_label.return_value = {
                "success": True,
                "label": {
                    "id": "lmao_team_critical_label",
                    "name": "critical",
                    "color": "#ef4444",
                    "team": {"id": "team_lmao", "key": "LMAO", "name": "Lmao Team"},
                },
            }

            # Test creating team-specific version
            result = await resolve_labels_with_autocreate(
                mock_context, ["critical"], team_id="team_lmao"
            )

            # Should have created new team-specific label
            assert len(result) == 1
            assert result[0]["id"] == "lmao_team_critical_label"
            assert result[0]["team"]["id"] == "team_lmao"

            # Should have created label for the team
            mock_client.create_label.assert_called_once_with(
                name="critical",
                team_id="team_lmao",
                color=ANY,
                description="Auto-created team-specific label for critical",
            )

    @pytest.mark.asyncio
    async def test_create_label_when_none_exist(self, mock_context):
        """Test that labels are created when they don't exist anywhere"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock empty labels response
            mock_client.get_labels.return_value = {"nodes": []}

            # Mock successful label creation
            mock_client.create_label.return_value = {
                "success": True,
                "label": {
                    "id": "new_urgent_label",
                    "name": "urgent",
                    "color": "#ff0000",
                    "team": {"id": "team_lmao", "key": "LMAO", "name": "Lmao Team"},
                },
            }

            # Test creating new label
            result = await resolve_labels_with_autocreate(
                mock_context, ["urgent"], team_id="team_lmao"
            )

            # Should have created the label
            assert len(result) == 1
            assert result[0]["id"] == "new_urgent_label"
            assert result[0]["name"] == "urgent"

            # Should have created label for the team
            mock_client.create_label.assert_called_once_with(
                name="urgent",
                team_id="team_lmao",
                color=ANY,
                description="Auto-created team-specific label for urgent",
            )


class TestMultiProjectSearch:
    """Test that project search finds issues from ALL projects with the same name"""

    @pytest.mark.asyncio
    async def test_resolve_multiple_projects_by_name(self, mock_context):
        """Test that resolve_projects_by_name returns all projects with matching names"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock projects response - multiple projects with same name in different teams
            mock_client.get_projects.return_value = {
                "nodes": [
                    {
                        "id": "proj_arcade_test_team1",
                        "name": "arcade-testing",
                        "description": "Testing project for Team 1",
                        "team": {"id": "team1", "name": "Team One"},
                    },
                    {
                        "id": "proj_arcade_test_team2",
                        "name": "arcade-testing",
                        "description": "Testing project for Team 2",
                        "team": {"id": "team2", "name": "Team Two"},
                    },
                    {
                        "id": "proj_other_project",
                        "name": "other-project",
                        "description": "Different project",
                        "team": {"id": "team1", "name": "Team One"},
                    },
                ]
            }

            # Test finding all "arcade-testing" projects
            projects = await resolve_projects_by_name(mock_context, "arcade-testing")

            # Should return both matching projects
            assert len(projects) == 2
            assert projects[0]["id"] == "proj_arcade_test_team1"
            assert projects[0]["name"] == "arcade-testing"
            assert projects[1]["id"] == "proj_arcade_test_team2"
            assert projects[1]["name"] == "arcade-testing"

    @pytest.mark.asyncio
    async def test_search_issues_with_multiple_projects(self, mock_context):
        """Test that search_issues finds issues from all projects with the same name"""
        with patch(
            "arcade_linear.tools.issues.resolve_projects_by_name"
        ) as mock_resolve_projects:
            with patch(
                "arcade_linear.tools.issues.LinearClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock multiple projects resolution
                mock_resolve_projects.return_value = [
                    {"id": "proj_arcade_test_team1", "name": "arcade-testing"},
                    {"id": "proj_arcade_test_team2", "name": "arcade-testing"},
                ]

                # Mock issues response
                mock_client.get_issues.return_value = {
                    "nodes": [
                        {
                            "id": "issue1",
                            "identifier": "T1-123",
                            "title": "Issue from Team 1 project",
                            "project": {
                                "id": "proj_arcade_test_team1",
                                "name": "arcade-testing",
                            },
                        },
                        {
                            "id": "issue2",
                            "identifier": "T2-456",
                            "title": "Issue from Team 2 project",
                            "project": {
                                "id": "proj_arcade_test_team2",
                                "name": "arcade-testing",
                            },
                        },
                    ],
                    "pageInfo": {"hasNextPage": False, "endCursor": "cursor"},
                }

                from arcade_linear.tools.issues import search_issues

                # Search for issues in "arcade-testing" project
                response = await search_issues(mock_context, project="arcade-testing")

                # Should have called resolve_projects_by_name instead of resolve_project_by_name
                mock_resolve_projects.assert_called_once_with(
                    mock_context, "arcade-testing"
                )

                # Should have called get_issues with project_ids filter for both projects
                mock_client.get_issues.assert_called_once()
                call_args = mock_client.get_issues.call_args
                filter_conditions = call_args.kwargs["filter_conditions"]

                # Should filter by both project IDs
                assert "project" in filter_conditions
                assert "id" in filter_conditions["project"]
                assert "in" in filter_conditions["project"]["id"]
                assert filter_conditions["project"]["id"]["in"] == [
                    "proj_arcade_test_team1",
                    "proj_arcade_test_team2",
                ]

                # Should return issues from both projects
                assert len(response["issues"]) == 2
                assert response["issues"][0]["identifier"] == "T1-123"
                assert response["issues"][1]["identifier"] == "T2-456"

    @pytest.mark.asyncio
    async def test_single_project_id_still_works(self, mock_context):
        """Test that providing a project ID still works with the new logic"""
        with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock issues response
            mock_client.get_issues.return_value = {
                "nodes": [
                    {
                        "id": "issue1",
                        "identifier": "T1-123",
                        "title": "Issue from specific project",
                        "project": {
                            "id": "project_12345",
                            "name": "specific-project",
                        },
                    }
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": "cursor"},
            }

            from arcade_linear.tools.issues import search_issues

            # Search with explicit project ID (starts with "project_")
            response = await search_issues(mock_context, project="project_12345")

            # Should have called get_issues with single project ID filter
            mock_client.get_issues.assert_called_once()
            call_args = mock_client.get_issues.call_args
            filter_conditions = call_args.kwargs["filter_conditions"]

            # Should filter by single project ID using 'in' operator
            assert "project" in filter_conditions
            assert "id" in filter_conditions["project"]
            assert "in" in filter_conditions["project"]["id"]
            assert filter_conditions["project"]["id"]["in"] == ["project_12345"]

            # Should return the issue
            assert len(response["issues"]) == 1
            assert response["issues"][0]["identifier"] == "T1-123"


class TestIssueRelationsAndData:
    """Test that issue relations, comments, and attachments are properly handled"""

    @pytest.mark.asyncio
    async def test_clean_issue_data_with_relations(self, mock_context):
        """Test that clean_issue_data properly handles relations data"""

        # Mock issue data with relations (dependencies/blockers)
        raw_issue_data = {
            "id": "issue_123",
            "identifier": "ARC-19",
            "title": "Issue with dependencies",
            "relations": {
                "nodes": [
                    {
                        "id": "relation_1",
                        "type": "blocks",
                        "relatedIssue": {
                            "id": "issue_456",
                            "identifier": "ARC-20",
                            "title": "Blocked issue",
                        },
                    },
                    {
                        "id": "relation_2",
                        "type": "blocked_by",
                        "relatedIssue": {
                            "id": "issue_789",
                            "identifier": "ARC-3",
                            "title": "Blocking issue",
                        },
                    },
                ]
            },
            "comments": {
                "nodes": [
                    {
                        "id": "comment_1",
                        "body": "This is a test comment",
                        "createdAt": "2024-01-01T00:00:00Z",
                        "user": {
                            "id": "user_1",
                            "name": "Test User",
                            "email": "test@example.com",
                        },
                    }
                ]
            },
        }

        # Clean the issue data
        cleaned = clean_issue_data(raw_issue_data)

        # Verify relations are properly cleaned
        assert "relations" in cleaned
        assert len(cleaned["relations"]) == 2

        # Check first relation (blocks)
        blocks_relation = cleaned["relations"][0]
        assert blocks_relation["id"] == "relation_1"
        assert blocks_relation["type"] == "blocks"
        assert blocks_relation["related_issue"]["identifier"] == "ARC-20"
        assert blocks_relation["related_issue"]["title"] == "Blocked issue"

        # Check second relation (blocked_by)
        blocked_by_relation = cleaned["relations"][1]
        assert blocked_by_relation["id"] == "relation_2"
        assert blocked_by_relation["type"] == "blocked_by"
        assert blocked_by_relation["related_issue"]["identifier"] == "ARC-3"
        assert blocked_by_relation["related_issue"]["title"] == "Blocking issue"

        # Verify comments are properly cleaned
        assert "comments" in cleaned
        assert len(cleaned["comments"]) == 1
        comment = cleaned["comments"][0]
        assert comment["id"] == "comment_1"
        assert comment["body"] == "This is a test comment"
        assert comment["user"]["name"] == "Test User"


class TestTemplateSupport:
    """Test that issue template functionality works correctly"""

    @pytest.mark.asyncio
    async def test_resolve_template_by_name(self, mock_context):
        """Test that template resolution works correctly"""
        with patch("arcade_linear.utils.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock templates response
            mock_client.get_templates.return_value = {
                "nodes": [
                    {
                        "id": "template_123",
                        "name": "User Onboarding Template",
                        "description": "Template for user onboarding issues",
                        "team": {"id": "team_456", "name": "Product"},
                        "templateData": {
                            "priority": 2,
                            "labels": ["onboarding", "user-experience"],
                        },
                    },
                    {
                        "id": "template_789",
                        "name": "Bug Report Template",
                        "description": "Template for bug reports",
                        "team": {"id": "team_456", "name": "Product"},
                        "templateData": {"priority": 3, "labels": ["bug"]},
                    },
                ]
            }

            from arcade_linear.utils import resolve_template_by_name

            # Test exact match
            template = await resolve_template_by_name(
                mock_context, "User Onboarding Template", "team_456"
            )

            assert template is not None
            assert template["id"] == "template_123"
            assert template["name"] == "User Onboarding Template"
            assert template["team"]["id"] == "team_456"

            # Test partial match
            template_partial = await resolve_template_by_name(
                mock_context, "Bug Report", "team_456"
            )

            assert template_partial is not None
            assert template_partial["id"] == "template_789"
            assert template_partial["name"] == "Bug Report Template"

            # Test not found
            template_none = await resolve_template_by_name(
                mock_context, "Nonexistent Template", "team_456"
            )
            assert template_none is None

    @pytest.mark.asyncio
    async def test_create_issue_with_template(self, mock_context):
        """Test that create_issue properly handles template parameter"""
        with patch(
            "arcade_linear.tools.issues.resolve_template_by_name"
        ) as mock_resolve_template:
            with patch(
                "arcade_linear.tools.issues.resolve_team_by_name"
            ) as mock_resolve_team:
                with patch(
                    "arcade_linear.tools.issues.LinearClient"
                ) as mock_client_class:
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client

                    # Mock team resolution
                    mock_resolve_team.return_value = {
                        "id": "team_456",
                        "name": "Product",
                        "key": "PROD",
                    }

                    # Mock template resolution
                    mock_resolve_template.return_value = {
                        "id": "template_123",
                        "name": "User Onboarding Template",
                        "description": "Template for user onboarding issues",
                        "team": {"id": "team_456", "name": "Product"},
                    }

                    # Mock successful issue creation
                    mock_client.create_issue.return_value = {
                        "success": True,
                        "issue": {
                            "id": "issue_new_123",
                            "identifier": "PROD-45",
                            "title": "New User Onboarding Issue",
                            "description": "Issue created from template",
                            "url": "https://linear.app/team/issue/PROD-45",
                        },
                    }

                    from arcade_linear.tools.issues import create_issue

                    # Test creating issue with template
                    response = await create_issue(
                        mock_context,
                        title="New User Onboarding Issue",
                        team="Product",
                        template="User Onboarding Template",
                    )

                    # Verify template was resolved
                    mock_resolve_template.assert_called_once_with(
                        mock_context, "User Onboarding Template", "team_456"
                    )

                    # Verify create_issue was called with templateId
                    mock_client.create_issue.assert_called_once()
                    call_args = mock_client.create_issue.call_args[0][0]
                    assert "templateId" in call_args
                    assert call_args["templateId"] == "template_123"

                    # Verify successful response
                    assert response["success"] is True
                    assert response["issue_identifier"] == "PROD-45"

    @pytest.mark.asyncio
    async def test_create_issue_template_not_found(self, mock_context):
        """Test error handling when template is not found"""
        with patch(
            "arcade_linear.tools.issues.resolve_template_by_name"
        ) as mock_resolve_template:
            with patch(
                "arcade_linear.tools.issues.resolve_team_by_name"
            ) as mock_resolve_team:
                # Mock team resolution
                mock_resolve_team.return_value = {
                    "id": "team_456",
                    "name": "Product",
                    "key": "PROD",
                }

                # Mock template not found
                mock_resolve_template.return_value = None

                from arcade_linear.tools.issues import create_issue

                # Test creating issue with non-existent template
                response = await create_issue(
                    mock_context,
                    title="Test Issue",
                    team="Product",
                    template="Nonexistent Template",
                )

                # Verify error response
                assert "error" in response
                assert "Template not found: Nonexistent Template" in response["error"]


class TestCycleSupport:
    """Test that cycle (sprint) functionality works correctly"""

    @pytest.mark.asyncio
    async def test_update_issue_with_current_cycle(self, mock_context):
        """Test that update_issue can add issue to current cycle"""
        with patch("arcade_linear.tools.issues.LinearClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock current issue
            mock_client.get_issue_by_id.return_value = {
                "id": "issue_123",
                "identifier": "TEST-123",
                "team": {"id": "team_456", "name": "Product"},
            }

            # Mock current cycle
            mock_client.get_current_cycle.return_value = {
                "id": "cycle_789",
                "number": 42,
                "name": "Sprint 42",
                "team": {"id": "team_456", "name": "Product"},
            }

            # Mock successful update
            mock_client.update_issue.return_value = {
                "success": True,
                "issue": {
                    "id": "issue_123",
                    "identifier": "TEST-123",
                    "title": "Test Issue",
                    "cycle": {"id": "cycle_789", "number": 42, "name": "Sprint 42"},
                },
            }

            from arcade_linear.tools.issues import update_issue

            # Test updating issue to current cycle
            response = await update_issue(
                mock_context, issue_id="TEST-123", cycle="current"
            )

            # Verify current cycle was retrieved
            mock_client.get_current_cycle.assert_called_once_with("team_456")

            # Verify update was called with cycle ID
            mock_client.update_issue.assert_called_once()
            call_args = mock_client.update_issue.call_args
            update_input = call_args[0][1]
            assert "cycleId" in update_input
            assert update_input["cycleId"] == "cycle_789"

            # Verify successful response
            assert response["success"] is True

    @pytest.mark.asyncio
    async def test_update_issue_with_cycle_name(self, mock_context):
        """Test that update_issue can resolve cycle by name"""
        with patch(
            "arcade_linear.tools.issues.resolve_cycle_by_name"
        ) as mock_resolve_cycle:
            with patch(
                "arcade_linear.tools.issues.LinearClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock current issue
                mock_client.get_issue_by_id.return_value = {
                    "id": "issue_123",
                    "identifier": "TEST-123",
                    "team": {"id": "team_456", "name": "Product"},
                }

                # Mock cycle resolution
                mock_resolve_cycle.return_value = {
                    "id": "cycle_789",
                    "number": 42,
                    "name": "Sprint 42",
                }

                # Mock successful update
                mock_client.update_issue.return_value = {
                    "success": True,
                    "issue": {
                        "id": "issue_123",
                        "identifier": "TEST-123",
                        "title": "Test Issue",
                    },
                }

                from arcade_linear.tools.issues import update_issue

                # Test updating issue with cycle name
                response = await update_issue(
                    mock_context, issue_id="TEST-123", cycle="Sprint 42"
                )

                # Verify cycle was resolved by name
                mock_resolve_cycle.assert_called_once_with(
                    mock_context, "Sprint 42", "team_456"
                )

                # Verify update was called with cycle ID
                mock_client.update_issue.assert_called_once()
                call_args = mock_client.update_issue.call_args
                update_input = call_args[0][1]
                assert "cycleId" in update_input
                assert update_input["cycleId"] == "cycle_789"

                # Verify successful response
                assert response["success"] is True

    @pytest.mark.asyncio
    async def test_create_issue_with_cycle(self, mock_context):
        """Test that create_issue can assign issue to cycle"""
        with patch(
            "arcade_linear.tools.issues.resolve_cycle_by_name"
        ) as mock_resolve_cycle:
            with patch(
                "arcade_linear.tools.issues.resolve_team_by_name"
            ) as mock_resolve_team:
                with patch(
                    "arcade_linear.tools.issues.LinearClient"
                ) as mock_client_class:
                    mock_client = AsyncMock()
                    mock_client_class.return_value = mock_client

                    # Mock team resolution
                    mock_resolve_team.return_value = {
                        "id": "team_456",
                        "name": "Product",
                        "key": "PROD",
                    }

                    # Mock cycle resolution
                    mock_resolve_cycle.return_value = {
                        "id": "cycle_789",
                        "number": 42,
                        "name": "Sprint 42",
                    }

                    # Mock successful issue creation
                    mock_client.create_issue.return_value = {
                        "success": True,
                        "issue": {
                            "id": "issue_new_123",
                            "identifier": "PROD-45",
                            "title": "New Issue",
                            "cycle": {
                                "id": "cycle_789",
                                "number": 42,
                                "name": "Sprint 42",
                            },
                        },
                    }

                    from arcade_linear.tools.issues import create_issue

                    # Test creating issue with cycle
                    response = await create_issue(
                        mock_context,
                        title="New Issue",
                        team="Product",
                        cycle="Sprint 42",
                    )

                    # Verify cycle was resolved
                    mock_resolve_cycle.assert_called_once_with(
                        mock_context, "Sprint 42", "team_456"
                    )

                    # Verify create_issue was called with cycleId
                    mock_client.create_issue.assert_called_once()
                    call_args = mock_client.create_issue.call_args[0][0]
                    assert "cycleId" in call_args
                    assert call_args["cycleId"] == "cycle_789"

                    # Verify successful response
                    assert response["success"] is True
                    assert response["issue_identifier"] == "PROD-45"

    @pytest.mark.asyncio
    async def test_get_current_cycle(self, mock_context):
        """Test that get_current_cycle tool works correctly"""
        with patch(
            "arcade_linear.tools.cycles.resolve_team_by_name"
        ) as mock_resolve_team:
            with patch(
                "arcade_linear.tools.cycles.LinearClient"
            ) as mock_client_class:
                mock_client = AsyncMock()
                mock_client_class.return_value = mock_client

                # Mock team resolution
                mock_resolve_team.return_value = {
                    "id": "team_456",
                    "name": "Product",
                    "key": "PROD",
                }

                # Mock current cycle
                mock_client.get_current_cycle.return_value = {
                    "id": "cycle_789",
                    "number": 42,
                    "name": "Sprint 42",
                    "startsAt": "2024-01-01T00:00:00Z",
                    "endsAt": "2024-01-14T23:59:59Z",
                    "progress": 0.5,
                    "team": {"id": "team_456", "name": "Product"},
                }

                from arcade_linear.tools.cycles import get_current_cycle

                # Test getting current cycle
                response = await get_current_cycle(mock_context, team="Product")

                # Verify team was resolved
                mock_resolve_team.assert_called_once_with(mock_context, "Product")

                # Verify current cycle was retrieved
                mock_client.get_current_cycle.assert_called_once_with("team_456")

                # Verify response structure
                assert "current_cycle" in response
                assert response["current_cycle"]["id"] == "cycle_789"
                assert response["current_cycle"]["name"] == "Sprint 42"
                assert response["current_cycle"]["number"] == 42


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
