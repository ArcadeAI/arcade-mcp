"""Linear workflow state management tools"""

from typing import Annotated, Any, Dict, List, Optional

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_linear.client import LinearClient
from arcade_linear.utils import (
    clean_workflow_state_data,
    remove_none_values,
    resolve_team_by_name,
)


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_workflow_states(
    context: ToolContext,
    team: Annotated[
        str,
        "Team name or ID to get workflow states for (e.g. 'Frontend', 'Backend', 'Product')."
    ],
) -> Annotated[Dict[str, Any], "List of workflow states for the team"]:
    """Get all workflow states (statuses) available for a specific team
    
    This tool shows all available status options for a team, which is helpful when:
    - You need to know what statuses are available before updating/creating issues
    - You're getting "status not found" errors and want to see valid options
    - You want to understand a team's workflow setup
    
    Workflow states represent the different statuses an issue can have, such as:
    - Backlog states: "Backlog", "To Do"  
    - Active states: "In Progress", "In Review"
    - Completion states: "Done", "Completed"
    - Other states: "Blocked", "On Hold"
    
    Each team can have its own custom workflow states with different names and types.
    """
    
    client = LinearClient(context.get_auth_token_or_empty())
    
    # Resolve team 
    team_id = None
    if team.startswith("team_"):  # Assume it's an ID
        team_id = team
    else:
        team_data = await resolve_team_by_name(context, team)
        if not team_data:
            return {"error": f"Team not found: {team}. Please check the team name and try again."}
        team_id = team_data["id"]
    
    # Get workflow states for this team
    try:
        states_response = await client.get_workflow_states(team_id=team_id)
        states = states_response.get("nodes", [])
        
        if not states:
            return {
                "team": team,
                "workflow_states": [],
                "message": "No workflow states found for this team. This is unusual - teams typically have default states."
            }
        
        # Clean and organize the states
        cleaned_states = []
        for state in states:
            cleaned_state = clean_workflow_state_data(state)
            cleaned_states.append(cleaned_state)
        
        # Group by type for better organization
        states_by_type = {}
        for state in cleaned_states:
            state_type = state.get("type", "unknown")
            if state_type not in states_by_type:
                states_by_type[state_type] = []
            states_by_type[state_type].append(state)
        
        return {
            "team": team,
            "team_id": team_id,
            "workflow_states": cleaned_states,
            "states_by_type": states_by_type,
            "total_count": len(cleaned_states),
            "available_status_names": [state["name"] for state in cleaned_states]
        }
        
    except Exception as e:
        return {"error": f"Failed to get workflow states for team {team}: {str(e)}"}


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["write"]))
async def create_workflow_state(
    context: ToolContext,
    team: Annotated[
        str,
        "Team name or ID to create the workflow state in (e.g. 'Frontend', 'Backend')."
    ],
    name: Annotated[
        str,
        "Name of the new workflow state (e.g. 'In Review', 'Ready for QA', 'Blocked')."
    ],
    type: Annotated[
        str,
        "Type of workflow state. Valid values: 'backlog', 'unstarted', 'started', 'completed', 'canceled'."
    ],
    description: Annotated[
        Optional[str],
        "Optional description explaining when this state should be used."
    ] = None,
    color: Annotated[
        Optional[str],
        "Optional hex color for the state (e.g. '#3b82f6'). If not provided, Linear will assign a default color."
    ] = None,
    position: Annotated[
        Optional[float],
        "Optional position in the workflow (lower numbers appear first). If not provided, will be added at the end."
    ] = None,
) -> Annotated[Dict[str, Any], "Created workflow state details"]:
    """Create a new workflow state (status) for a team
    
    This tool creates custom workflow states that teams can use to track issue progress.
    Use this when you need a status that doesn't exist yet.
    
    **Workflow State Types:**
    - **backlog**: Issues waiting to be started (e.g. "Backlog", "To Do")
    - **unstarted**: Issues ready but not yet begun (e.g. "Ready", "Planned")  
    - **started**: Issues actively being worked on (e.g. "In Progress", "In Review")
    - **completed**: Finished issues (e.g. "Done", "Deployed", "Resolved")
    - **canceled**: Issues that won't be completed (e.g. "Canceled", "Won't Fix")
    
    **Common Examples:**
    - create_workflow_state(team="Frontend", name="In Review", type="started")
    - create_workflow_state(team="Backend", name="Ready for QA", type="started") 
    - create_workflow_state(team="Product", name="Needs Approval", type="started")
    - create_workflow_state(team="Design", name="Design Complete", type="completed")
    
    **Tips:**
    - Choose descriptive names that clearly indicate what the status means
    - Use the appropriate type to ensure proper workflow behavior
    - Consider the position to place the state in the right order
    """
    
    client = LinearClient(context.get_auth_token_or_empty())
    
    # Validate type
    valid_types = ["backlog", "unstarted", "started", "completed", "canceled"]
    if type.lower() not in valid_types:
        return {"error": f"Invalid workflow state type '{type}'. Valid types: {', '.join(valid_types)}"}
    
    # Resolve team
    team_id = None
    team_name = None
    if team.startswith("team_"):  # Assume it's an ID
        team_id = team
        # Try to get team name for response
        try:
            teams_response = await client.get_teams(first=100)
            for t in teams_response.get("nodes", []):
                if t["id"] == team_id:
                    team_name = t["name"]
                    break
        except:
            team_name = team_id
    else:
        team_data = await resolve_team_by_name(context, team)
        if not team_data:
            return {"error": f"Team not found: {team}. Please check the team name and try again."}
        team_id = team_data["id"]
        team_name = team_data["name"]
    
    # Check if workflow state already exists
    try:
        existing_states = await client.get_workflow_states(team_id=team_id)
        for state in existing_states.get("nodes", []):
            if state["name"].lower() == name.lower():
                return {
                    "error": f"Workflow state '{name}' already exists for team '{team_name}'. "
                           f"Existing state ID: {state['id']}"
                }
    except Exception:
        # If we can't check existing states, continue with creation
        pass
    
    # Build creation input
    create_input = {
        "name": name,
        "type": type.lower(),
        "teamId": team_id,
    }
    
    if description:
        create_input["description"] = description
    if color:
        create_input["color"] = color
    if position is not None:
        create_input["position"] = position
    
    # Create the workflow state
    try:
        result = await client.create_workflow_state(create_input)
        
        if result.get("success") and result.get("workflowState"):
            workflow_state = result["workflowState"]
            return {
                "success": True,
                "message": f"Successfully created workflow state '{name}' for team '{team_name}'",
                "workflow_state": clean_workflow_state_data(workflow_state),
                "team": team_name,
                "team_id": team_id,
            }
        else:
            return {
                "success": False,
                "error": f"Failed to create workflow state '{name}'. " + 
                        result.get("error", "Unknown error occurred.")
            }
            
    except Exception as e:
        error_msg = str(e).lower()
        if "duplicate" in error_msg or "already exists" in error_msg:
            return {
                "error": f"Workflow state '{name}' already exists for team '{team_name}'. "
                        f"Use get_workflow_states to see existing states."
            }
        else:
            return {"error": f"Failed to create workflow state '{name}': {str(e)}"} 