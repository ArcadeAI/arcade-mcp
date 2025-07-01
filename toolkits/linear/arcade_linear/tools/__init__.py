"""Linear tools for Arcade AI"""

from arcade_linear.tools.cycles import (
    get_current_cycle,
    get_cycle_issues,
    list_cycles,
)
from arcade_linear.tools.issues import (
    add_comment_to_issue,
    create_issue,
    get_issue,
    get_templates,
    search_issues,
    update_issue,
)
from arcade_linear.tools.projects import (
    get_projects,
)
from arcade_linear.tools.teams import get_teams
from arcade_linear.tools.users import (
    get_users,
)
from arcade_linear.tools.workflows import (
    create_workflow_state,
    get_workflow_states,
)

__all__ = [
    # Team tools
    "get_teams",
    # Issue tools - Primary tools for all issue management
    "search_issues",  # Primary tool for ALL issue filtering and finding
    "get_issue",  # Get specific issue details
    "update_issue",  # Handles ALL issue updates including labels, assignees, status
    "create_issue",  # Create new issues, tasks, bugs with automatic label creation
    "add_comment_to_issue",  # Add comments to issues for documentation
    "get_templates",  # Get available issue templates for structured issue creation
    # User tools
    "get_users",
    # Project tools
    "get_projects",
    # Workflow state tools
    "get_workflow_states",  # List available statuses for a team
    "create_workflow_state",  # Create new workflow states (statuses)
    # Cycle/sprint tools
    "get_current_cycle",  # Get the current active cycle for a team
    "list_cycles",  # List cycles/sprints for a team
    "get_cycle_issues",  # Get issues in a specific cycle
]
