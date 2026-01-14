"""Tests for Attio activity operations (notes and tasks)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from arcade_attio.tools.activity import (
    create_note,
    create_task,
    list_tasks,
)


class TestCreateNote:
    """Tests for create_note tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_note(self, mock_context):
        """Test creating a note on a record."""
        mock_response = {
            "data": {
                "id": {"note_id": "note-123"},
            }
        }

        with patch(
            "arcade_attio.tools.activity._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await create_note(
                mock_context,
                parent_object="companies",
                parent_record_id="record-abc",
                title="Meeting Notes",
                content="Discussed Q1 goals.",
            )

            assert result["note_id"] == "note-123"
            assert result["status"] == "created"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_note_markdown(self, mock_context):
        """Test creating a note with markdown format."""
        mock_response = {
            "data": {
                "id": {"note_id": "note-456"},
            }
        }

        with patch(
            "arcade_attio.tools.activity._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await create_note(
                mock_context,
                parent_object="people",
                parent_record_id="person-123",
                title="Call Summary",
                content="# Summary\n- Item 1\n- Item 2",
                format_type="markdown",
            )

            assert result["note_id"] == "note-456"
            call_args = mock_request.call_args
            assert call_args[0][2]["data"]["format"] == "markdown"


class TestCreateTask:
    """Tests for create_task tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_create_task(self, mock_context):
        """Test creating a task."""
        mock_response = {
            "data": {
                "id": {"task_id": "task-123"},
            }
        }

        with patch(
            "arcade_attio.tools.activity._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await create_task(
                mock_context,
                content="Follow up with Acme Corp",
                assignee_id="member-abc",
                deadline="2026-01-20T00:00:00.000Z",
            )

            assert result["task_id"] == "task-123"
            assert result["status"] == "created"
            assert result["deadline"] == "2026-01-20T00:00:00.000Z"

    @pytest.mark.asyncio
    async def test_create_task_with_linked_records(self, mock_context):
        """Test creating a task linked to records."""
        mock_response = {
            "data": {
                "id": {"task_id": "task-456"},
            }
        }

        with patch(
            "arcade_attio.tools.activity._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            linked_records = [{"target_object": "companies", "target_record_id": "company-abc"}]
            result = await create_task(
                mock_context,
                content="Review proposal",
                assignee_id="member-def",
                deadline="2026-02-01T00:00:00.000Z",
                linked_records=linked_records,
            )

            assert result["task_id"] == "task-456"
            call_args = mock_request.call_args
            assert call_args[0][2]["data"]["linked_records"] == linked_records


class TestListTasks:
    """Tests for list_tasks tool."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ToolContext."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_list_tasks(self, mock_context):
        """Test listing tasks."""
        mock_response = {
            "data": [
                {
                    "id": {"task_id": "task-1"},
                    "content": "Follow up with Acme",
                    "deadline_at": "2026-01-20T00:00:00.000Z",
                    "is_completed": False,
                },
                {
                    "id": {"task_id": "task-2"},
                    "content": "Send proposal",
                    "deadline_at": "2026-01-25T00:00:00.000Z",
                    "is_completed": True,
                },
            ]
        }

        with patch(
            "arcade_attio.tools.activity._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await list_tasks(mock_context)

            assert result["total"] == 2
            assert result["tasks"][0]["content"] == "Follow up with Acme"
            assert result["tasks"][1]["is_completed"] is True

    @pytest.mark.asyncio
    async def test_list_tasks_filtered(self, mock_context):
        """Test listing tasks with filters."""
        mock_response = {"data": []}

        with patch(
            "arcade_attio.tools.activity._attio_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            result = await list_tasks(
                mock_context,
                assignee_id="member-abc",
                is_completed=False,
                limit=10,
            )

            assert result["total"] == 0
            call_args = mock_request.call_args
            endpoint = call_args[0][1]
            assert "assignee=member-abc" in endpoint
            assert "is_completed=false" in endpoint
            assert "limit=10" in endpoint
