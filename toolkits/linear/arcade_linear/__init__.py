"""Linear Toolkit for Arcade AI - Comprehensive Linear API Integration"""

from arcade_linear.tools import (
    # Issue management - Primary tools for all issue operations
    search_issues,  # Primary tool for ALL issue filtering and finding
    get_issue,      # Get specific issue details
    update_issue,   # Handles ALL issue updates including labels, assignees, status
    create_issue,   # Create new issues, tasks, bugs with automatic label creation
    add_comment_to_issue,  # Add comments to issues for documentation
    get_templates,  # Get available issue templates for structured issue creation
    
    # User and team management
    get_users,
    get_teams,
    
    # Project management
    get_projects,
    
    # Workflow state management
    get_workflow_states,   # List available statuses for a team
    create_workflow_state, # Create new workflow states (statuses)
    
    # Cycle/sprint management
    get_current_cycle,     # Get the current active cycle for a team
    list_cycles,           # List cycles/sprints for a team
    get_cycle_issues,      # Get issues in a specific cycle
)

__all__ = [
    # Core issue tools - Primary tools for all issue management
    "search_issues",
    "get_issue", 
    "update_issue",
    "create_issue",
    "add_comment_to_issue",
    "get_templates",
    
    # User and team tools
    "get_users",
    "get_teams",
    
    # Project tools
    "get_projects",
    
    # Workflow state tools
    "get_workflow_states",
    "create_workflow_state",
    
    # Cycle/sprint tools
    "get_current_cycle",
    "list_cycles",
    "get_cycle_issues",
]

__version__ = "1.0.0"
