"""
This module contains all mock data used across the test suite, organized by category:
- API response formats (what Todoist API returns)
- Parsed response formats (what our functions return after processing)
- Test scenario specific data
"""

PROJECTS_API_RESPONSE = {
    "results": [
        {
            "id": "project_123",
            "name": "Work Project",
            "created_at": "2021-01-01",
            "can_assign_tasks": True,
            "child_order": 0,
            "color": "blue",
            "creator_uid": "user_123",
            "is_archived": False,
            "is_deleted": False,
            "is_favorite": True,
        },
        {
            "id": "project_456",
            "name": "Personal Tasks",
            "created_at": "2021-01-01",
            "can_assign_tasks": True,
            "child_order": 1,
            "color": "red",
            "creator_uid": "user_123",
            "is_archived": False,
            "is_deleted": False,
            "is_favorite": False,
        },
    ]
}

PROJECTS_PARSED_RESPONSE = {
    "projects": [
        {"id": "project_123", "name": "Work Project", "created_at": "2021-01-01"},
        {"id": "project_456", "name": "Personal Tasks", "created_at": "2021-01-01"},
    ]
}

SINGLE_TASK_API_RESPONSE = {
    "results": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": True,
            "description": "Description of the task",
        }
    ],
    "next_cursor": None,
}

TASKS_WITH_PAGINATION_API_RESPONSE = {
    "results": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": True,
            "description": "Description of the task",
        }
    ],
    "next_cursor": "next_page_cursor_123",
}

MULTIPLE_TASKS_API_RESPONSE = {
    "results": [
        {
            "id": "1",
            "content": "Buy groceries",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": False,
            "description": "Need to buy weekly groceries",
        },
        {
            "id": "2",
            "content": "Grocery shopping",
            "added_at": "2021-01-01",
            "priority": 2,
            "project_id": "project_456",
            "checked": False,
            "description": "Similar to grocery task",
        },
        {
            "id": "3",
            "content": "Meeting notes",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": False,
            "description": "Take notes during meeting",
        },
    ],
    "next_cursor": None,
}

PROJECT_SPECIFIC_TASKS_API_RESPONSE = {
    "results": [
        {
            "id": "1",
            "content": "Buy groceries",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": False,
            "description": "Need to buy weekly groceries",
        },
        {
            "id": "3",
            "content": "Meeting notes",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": False,
            "description": "Take notes during meeting",
        },
    ],
    "next_cursor": None,
}

EMPTY_TASKS_API_RESPONSE = {
    "results": [],
    "next_cursor": None,
}

CREATE_TASK_API_RESPONSE = {
    "id": "2",
    "content": "New Task",
    "added_at": "2024-01-01",
    "project_id": "project_123",
    "checked": False,
    "priority": 1,
    "description": "A new task description",
}

CUSTOM_LIMIT_TASK_API_RESPONSE = {
    "results": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": False,
            "description": "Description",
        },
    ],
    "next_cursor": None,
}

PAGINATED_TASKS_API_RESPONSE = {
    "results": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "priority": 1,
            "project_id": "project_123",
            "checked": False,
            "description": "Description",
        },
    ],
    "next_cursor": "next_page_token_456",
}

SINGLE_TASK_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": True,
        }
    ],
    "next_page_token": None,
}

TASKS_WITH_PAGINATION_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": True,
        }
    ],
    "next_page_token": "next_page_cursor_123",
}

MULTIPLE_TASKS_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "1",
            "content": "Buy groceries",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
        {
            "id": "2",
            "content": "Grocery shopping",
            "added_at": "2021-01-01",
            "project_id": "project_456",
            "checked": False,
        },
        {
            "id": "3",
            "content": "Meeting notes",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
    ],
    "next_page_token": None,
}

PROJECT_SPECIFIC_TASKS_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "1",
            "content": "Buy groceries",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
        {
            "id": "3",
            "content": "Meeting notes",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
    ],
    "next_page_token": None,
}

EMPTY_TASKS_PARSED_RESPONSE = {
    "tasks": [],
    "next_page_token": None,
}

CREATE_TASK_PARSED_RESPONSE = {
    "id": "2",
    "content": "New Task",
    "added_at": "2024-01-01",
    "project_id": "project_123",
    "checked": False,
}

CUSTOM_LIMIT_TASK_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
    ],
    "next_page_token": None,
}

PAGINATED_TASKS_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "1",
            "content": "Task 1",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
    ],
    "next_page_token": "next_page_token_456",
}

PARTIAL_MATCH_TASKS_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "1",
            "content": "Complete task A",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
        {
            "id": "2",
            "content": "Complete task B",
            "added_at": "2021-01-01",
            "project_id": "project_456",
            "checked": False,
        },
    ],
    "next_page_token": None,
}

SINGLE_MATCH_TASK_PARSED_RESPONSE = {
    "tasks": [
        {
            "id": "3",
            "content": "Meeting notes",
            "added_at": "2021-01-01",
            "project_id": "project_123",
            "checked": False,
        },
    ],
    "next_page_token": None,
}

CLOSE_TASK_SUCCESS_RESPONSE = {"message": "Task closed successfully"}

DELETE_TASK_SUCCESS_RESPONSE = {"message": "Task deleted successfully"}
