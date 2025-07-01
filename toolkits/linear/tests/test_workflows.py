"""Tests for Linear workflow state management tools"""

from unittest.mock import AsyncMock, patch

import pytest

from arcade_linear.tools.workflows import (
    create_workflow_state,
    get_workflow_states,
)


class TestGetWorkflowStates:
    """Tests for get_workflow_states tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_get_workflow_states_success(self, mock_client_class, mock_context):
        """Test successful workflow states retrieval"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_workflow_states.return_value = {
            "nodes": [
                {
                    "id": "state_1",
                    "name": "To Do",
                    "type": "unstarted",
                    "color": "#e2e8f0",
                    "position": 1,
                    "team": {"id": "team_1", "key": "FE", "name": "Frontend"},
                },
                {
                    "id": "state_2",
                    "name": "In Progress",
                    "type": "started",
                    "color": "#3b82f6",
                    "position": 2,
                    "team": {"id": "team_1", "key": "FE", "name": "Frontend"},
                },
                {
                    "id": "state_3",
                    "name": "Done",
                    "type": "completed",
                    "color": "#10b981",
                    "position": 3,
                    "team": {"id": "team_1", "key": "FE", "name": "Frontend"},
                },
            ]
        }

        # Mock team resolution
        with patch("arcade_linear.tools.workflows.resolve_team_by_name") as mock_resolve_team:
            mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}

            # Call function
            result = await get_workflow_states(mock_context, "Frontend")

            # Assertions
            assert result["team"] == "Frontend"
            assert result["team_id"] == "team_1"
            assert result["total_count"] == 3
            assert len(result["workflow_states"]) == 3
            assert "To Do" in result["available_status_names"]
            assert "In Progress" in result["available_status_names"]
            assert "Done" in result["available_status_names"]

            # Check states are grouped by type
            assert "unstarted" in result["states_by_type"]
            assert "started" in result["states_by_type"]
            assert "completed" in result["states_by_type"]

            mock_client.get_workflow_states.assert_called_once_with(team_id="team_1")

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_get_workflow_states_team_not_found(self, mock_client_class, mock_context):
        """Test workflow states retrieval with invalid team"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock team resolution failure
        with patch("arcade_linear.tools.workflows.resolve_team_by_name") as mock_resolve_team:
            mock_resolve_team.return_value = None

            # Call function
            result = await get_workflow_states(mock_context, "NonExistent")

            # Assertions
            assert "error" in result
            assert "Team not found" in result["error"]

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_get_workflow_states_empty_result(self, mock_client_class, mock_context):
        """Test workflow states retrieval with no states"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_workflow_states.return_value = {"nodes": []}

        # Mock team resolution
        with patch("arcade_linear.tools.workflows.resolve_team_by_name") as mock_resolve_team:
            mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}

            # Call function
            result = await get_workflow_states(mock_context, "Frontend")

            # Assertions
            assert result["team"] == "Frontend"
            assert result["workflow_states"] == []
            assert "No workflow states found" in result["message"]


class TestCreateWorkflowState:
    """Tests for create_workflow_state tool"""

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_create_workflow_state_success(self, mock_client_class, mock_context):
        """Test successful workflow state creation"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_workflow_states.return_value = {"nodes": []}  # No existing states
        mock_client.create_workflow_state.return_value = {
            "success": True,
            "workflowState": {
                "id": "state_new",
                "name": "In Review",
                "type": "started",
                "color": "#8b5cf6",
                "position": 2,
                "team": {"id": "team_1", "key": "FE", "name": "Frontend"},
            },
        }

        # Mock team resolution
        with patch("arcade_linear.tools.workflows.resolve_team_by_name") as mock_resolve_team:
            mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}

            # Call function
            result = await create_workflow_state(
                mock_context, team="Frontend", name="In Review", type="started"
            )

            # Assertions
            assert result["success"] is True
            assert "Successfully created workflow state" in result["message"]
            assert result["workflow_state"]["name"] == "In Review"
            assert result["team"] == "Frontend"

            mock_client.create_workflow_state.assert_called_once()
            call_args = mock_client.create_workflow_state.call_args[0][0]
            assert call_args["name"] == "In Review"
            assert call_args["type"] == "started"
            assert call_args["teamId"] == "team_1"

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_create_workflow_state_invalid_type(self, mock_client_class, mock_context):
        """Test workflow state creation with invalid type"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Call function with invalid type
        result = await create_workflow_state(
            mock_context, team="Frontend", name="In Review", type="invalid_type"
        )

        # Assertions
        assert "error" in result
        assert "Invalid workflow state type" in result["error"]
        assert "backlog, unstarted, started, completed, canceled" in result["error"]

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_create_workflow_state_already_exists(self, mock_client_class, mock_context):
        """Test workflow state creation when state already exists"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_workflow_states.return_value = {
            "nodes": [{"id": "state_1", "name": "In Review", "type": "started"}]
        }

        # Mock team resolution
        with patch("arcade_linear.tools.workflows.resolve_team_by_name") as mock_resolve_team:
            mock_resolve_team.return_value = {"id": "team_1", "name": "Frontend"}

            # Call function
            result = await create_workflow_state(
                mock_context, team="Frontend", name="In Review", type="started"
            )

            # Assertions
            assert "error" in result
            assert "already exists" in result["error"]

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_create_workflow_state_team_not_found(self, mock_client_class, mock_context):
        """Test workflow state creation with invalid team"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock team resolution failure
        with patch("arcade_linear.tools.workflows.resolve_team_by_name") as mock_resolve_team:
            mock_resolve_team.return_value = None

            # Call function
            result = await create_workflow_state(
                mock_context, team="NonExistent", name="In Review", type="started"
            )

            # Assertions
            assert "error" in result
            assert "Team not found" in result["error"]

    @pytest.mark.asyncio
    @patch("arcade_linear.tools.workflows.LinearClient")
    async def test_create_workflow_state_with_optional_params(
        self, mock_client_class, mock_context
    ):
        """Test workflow state creation with optional parameters"""
        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        mock_client.get_workflow_states.return_value = {"nodes": []}
        mock_client.create_workflow_state.return_value = {
            "success": True,
            "workflowState": {
                "id": "state_new",
                "name": "Ready for QA",
                "description": "Ready for quality assurance testing",
                "type": "started",
                "color": "#f59e0b",
                "position": 1.5,
                "team": {"id": "team_1", "key": "BE", "name": "Backend"},
            },
        }

        # Mock team resolution
        with patch("arcade_linear.tools.workflows.resolve_team_by_name") as mock_resolve_team:
            mock_resolve_team.return_value = {"id": "team_1", "name": "Backend"}

            # Call function with optional parameters
            result = await create_workflow_state(
                mock_context,
                team="Backend",
                name="Ready for QA",
                type="started",
                description="Ready for quality assurance testing",
                color="#f59e0b",
                position=1.5,
            )

            # Assertions
            assert result["success"] is True
            assert result["workflow_state"]["description"] == "Ready for quality assurance testing"

            call_args = mock_client.create_workflow_state.call_args[0][0]
            assert call_args["description"] == "Ready for quality assurance testing"
            assert call_args["color"] == "#f59e0b"
            assert call_args["position"] == 1.5
