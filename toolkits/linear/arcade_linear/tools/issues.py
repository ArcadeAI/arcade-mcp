from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2

from arcade_linear.client import LinearClient
from arcade_linear.types import (
    IssueSortField,
    SortDirection,
)
from arcade_linear.utils import (
    _auto_transition_backlog_to_todo,
    _set_todo_status_for_sprint_creation,
    add_pagination_info,
    build_issue_filter,
    clean_issue_data,
    clean_template_data,
    is_relative_date_range_term,
    normalize_priority,
    parse_date_range_for_relative_terms,
    parse_date_string,
    remove_none_values,
    resolve_cycle_by_name,
    resolve_cycle_by_relative_reference,
    resolve_issue_with_team_info,
    resolve_labels_read_only,
    resolve_labels_with_autocreate,
    resolve_project_by_name,
    resolve_projects_by_name,
    resolve_team_by_name,
    resolve_template_by_name,
    resolve_user_by_email_or_name,
    resolve_workflow_state_by_name,
    validate_date_format,
)


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def search_issues(
    context: ToolContext,
    keywords: Annotated[
        str | None,
        "Search terms to find in issue titles and descriptions. Supports partial matches.",
    ] = None,
    team: Annotated[
        str | None,
        "Team name or ID to filter issues by. Defaults to None (all teams).",
    ] = None,
    status: Annotated[
        str | None,
        "Workflow state name to filter by (e.g. 'To Do', 'In Progress', 'Done', 'Backlog'). "
        "Defaults to None (all statuses).",
    ] = None,
    assignee: Annotated[
        str | None,
        "Assignee filter. Use 'me' for current user, 'unassigned' for unassigned issues, "
        "or provide user name/email. Defaults to None (all assignees).",
    ] = None,
    creator: Annotated[
        str | None,
        "Filter by issue creator. Use 'me' for current user, or provide user name/email. "
        "Defaults to None (all creators).",
    ] = None,
    priority: Annotated[
        str | None,
        "Priority level filter. Valid values: 'urgent', 'high', 'medium', 'low', 'none'. "
        "Defaults to None (all priorities).",
    ] = None,
    labels: Annotated[
        list[str] | None,
        "List of label names to filter by (e.g. ['bug', 'critical']). Issues must have ALL labels. "
        "Defaults to None (no label filtering).",
    ] = None,
    project: Annotated[
        str | None,
        "Project name or ID to filter issues by. Defaults to None (all projects).",
    ] = None,
    created_after: Annotated[
        str | None,
        "Find issues created after this date. Format: YYYY-MM-DD or relative like 'last week'. "
        "Defaults to None (no date filtering).",
    ] = None,
    created_before: Annotated[
        str | None,
        "Find issues created before this date. Format: YYYY-MM-DD or relative like 'today'. "
        "Defaults to None (no date filtering).",
    ] = None,
    updated_after: Annotated[
        str | None,
        "Find issues updated after this date. Format: YYYY-MM-DD or relative like 'yesterday'. "
        "Defaults to None (no date filtering).",
    ] = None,
    updated_before: Annotated[
        str | None,
        "Find issues updated before this date. Format: YYYY-MM-DD or relative like 'last month'. "
        "Defaults to None (no date filtering).",
    ] = None,
    sort_by: Annotated[
        IssueSortField, "Field to sort results by. Defaults to UPDATED_AT."
    ] = IssueSortField.UPDATED_AT,
    sort_direction: Annotated[
        SortDirection, "Sort direction. Defaults to DESC (most recent first)."
    ] = SortDirection.DESC,
    limit: Annotated[
        int, "Maximum number of issues to return. Min 1, max 100. Defaults to 50."
    ] = 50,
    after_cursor: Annotated[
        str | None,
        "Pagination cursor for getting more results. Use 'end_cursor' from previous response.",
    ] = None,
) -> Annotated[dict[str, Any], "Filtered and sorted issues with search metadata"]:
    """PRIMARY ISSUE FINDER - Search and filter Linear issues with comprehensive criteria

    This is the MAIN tool for finding issues in Linear. Use this tool for ANY issue
    search or filtering need.

    WHEN TO USE THIS TOOL (Primary scenarios):
    - "Find all high-priority bugs assigned to me" - Use this with priority='high', labels=['bug'], assignee='me'
    - "Show me In Progress issues in Frontend team" - Use this with status='In Progress', team='Frontend'
    - "Find authentication issues" - Use this with keywords='authentication'
    - "Show completed issues from last week" - Use this with status='Done', updated_after='last week'
    - "Find unassigned critical bugs" - Use this with assignee='unassigned', labels=['critical', 'bug']
    - "Get all Backend team issues" - Use this with team='Backend'
    - "Find all issues currently In Progress" - Use this with status='In Progress'
    - "Show completed issues from last week" - Use this with status='Done', updated_after='last week'
    - "Find To Do issues in Backend team" - Use this with status='To Do', team='Backend'
    - ANY combination of filters (team + status + priority + assignee + dates + labels)

    When NOT to use this tool:
    - Getting a specific issue by ID/identifier - Use get_issue instead
    - Creating or updating issues - Use create_issue/update_issue instead

    This tool replaces multiple specialized search tools and handles ALL issue finding scenarios.
    It's optimized for complex filtering and should be your first choice for issue queries.
    """

    # Validate inputs
    limit = max(1, min(limit, 100))

    # Validate date formats
    for date_field, date_value in [
        ("created_after", created_after),
        ("created_before", created_before),
        ("updated_after", updated_after),
        ("updated_before", updated_before),
    ]:
        if date_value:
            validate_date_format(date_field, date_value)

    # Parse dates with improved relative date range handling
    created_after_date = None
    created_before_date = None
    if created_after:
        if is_relative_date_range_term(created_after):
            range_start, range_end = parse_date_range_for_relative_terms(
                created_after
            )
            created_after_date = range_start
            if created_before is None:
                created_before_date = range_end
        else:
            created_after_date = parse_date_string(created_after)

    if created_before and created_before_date is None:
        if is_relative_date_range_term(created_before):
            range_start, range_end = parse_date_range_for_relative_terms(
                created_before
            )
            created_before_date = range_end
        else:
            created_before_date = parse_date_string(created_before)

    # Handle updated_after with special logic for relative ranges
    updated_after_date = None
    updated_before_date = None
    if updated_after:
        if is_relative_date_range_term(updated_after):
            # For relative terms like "last week", parse as a proper date range
            range_start, range_end = parse_date_range_for_relative_terms(
                updated_after
            )
            updated_after_date = range_start
            # If this is a range term and no explicit updated_before was provided, use the range end
            if updated_before is None:
                updated_before_date = range_end
        else:
            # For specific dates, parse normally
            updated_after_date = parse_date_string(updated_after)

    # Handle updated_before (only if not already set by range logic above)
    if updated_before and updated_before_date is None:
        if is_relative_date_range_term(updated_before):
            range_start, range_end = parse_date_range_for_relative_terms(
                updated_before
            )
            updated_before_date = range_end
        else:
            updated_before_date = parse_date_string(updated_before)

    client = LinearClient(context.get_auth_token_or_empty())

    # Resolve team if provided
    team_id = None
    if team:
        if team.startswith("team_"):  # Assume it's an ID
            team_id = team
        else:
            team_data = await resolve_team_by_name(context, team)
            if team_data:
                team_id = team_data["id"]
            else:
                # Get available teams to help the user
                try:
                    client = LinearClient(context.get_auth_token_or_empty())
                    teams_response = await client.get_teams(first=20)
                    available_teams = teams_response.get("nodes", [])

                    if available_teams:
                        team_names = [
                            t["name"] for t in available_teams[:10]
                        ]  # Show up to 10 teams
                        team_list = "', '".join(team_names)
                        if len(available_teams) > 10:
                            return {
                                "error": f"Team '{team}' not found. Available teams include: '{team_list}' and {len(available_teams) - 10} others. Use 'get_teams' tool to see all teams, then specify the correct team name."
                            }
                        else:
                            return {
                                "error": f"Team '{team}' not found. Available teams: '{team_list}'. Please specify one of these existing team names."
                            }
                    else:
                        return {
                            "error": f"Team '{team}' not found and no teams could be retrieved. Please check the team name or use 'get_teams' tool to see available teams."
                        }
                except Exception:
                    return {
                        "error": f"Team '{team}' not found. Please check the team name or use 'get_teams' tool to see available teams."
                    }

    # Resolve assignee if provided
    assignee_id = None
    if assignee:
        if assignee.lower() == "me":
            viewer = await client.get_viewer()
            assignee_id = viewer["id"]
        elif assignee.lower() == "unassigned":
            assignee_id = "unassigned"  # Special marker for null filter
        elif assignee.startswith("user_"):  # Assume it's an ID
            assignee_id = assignee
        else:
            user_data = await resolve_user_by_email_or_name(context, assignee)
            if user_data:
                assignee_id = user_data["id"]

    # Resolve creator if provided
    creator_id = None
    if creator:
        if creator.lower() == "me":
            viewer = await client.get_viewer()
            creator_id = viewer["id"]
        elif creator.startswith("user_"):  # Assume it's an ID
            creator_id = creator
        else:
            user_data = await resolve_user_by_email_or_name(context, creator)
            if user_data:
                creator_id = user_data["id"]

    # Resolve workflow state if provided
    state_id = None
    if status:
        if status.startswith("state_"):  # Assume it's an ID
            state_id = status
        else:
            state_data = await resolve_workflow_state_by_name(
                context, status, team_id
            )
            if state_data:
                state_id = state_data["id"]

    # Resolve project(s) if provided - support multiple projects with same name
    project_ids = None
    if project:
        if project.startswith("project_"):  # Assume it's an ID
            project_ids = [project]  # Single project ID as list
        else:
            # Use multi-project resolution to find ALL projects with this name
            project_data_list = await resolve_projects_by_name(context, project)
            if project_data_list:
                project_ids = [proj["id"] for proj in project_data_list]
            else:
                # No projects found with the given name - return helpful error
                return {
                    "error": f"Project '{project}' not found. Please check the project name and try again.",
                    "issues": [],
                    "total_count": 0,
                    "search_criteria": {
                        "keywords": keywords,
                        "team": team,
                        "status": status,
                        "assignee": assignee,
                        "creator": creator,
                        "priority": priority,
                        "labels": labels,
                        "project": project,
                        "created_after": created_after,
                        "created_before": created_before,
                        "updated_after": updated_after,
                        "updated_before": updated_before,
                        "sort_by": sort_by.value,
                        "sort_direction": sort_direction.value,
                    },
                }

    # Resolve labels if provided (read-only for search)
    label_ids = []
    if labels:
        label_data = await resolve_labels_read_only(context, labels, team_id)
        label_ids = [label["id"] for label in label_data]

    # Normalize priority
    priority_value = normalize_priority(priority) if priority else None

    # Build filter
    issue_filter = build_issue_filter(
        team_id=team_id,
        assignee_id=assignee_id,
        creator_id=creator_id,
        state_id=state_id,
        priority=priority_value,
        label_ids=label_ids if label_ids else None,
        project_ids=project_ids,
        created_at_gte=created_after_date,
        created_at_lte=created_before_date,
        updated_at_gte=updated_after_date,
        updated_at_lte=updated_before_date,
        search_query=keywords,
    )

    # Build order by - Linear API expects simple camelCase enum values
    # Direction is not supported in the orderBy parameter, just use the field name
    order_by = sort_by.value

    # Search issues
    issues_response = await client.get_issues(
        first=limit,
        after=after_cursor,
        filter_conditions=issue_filter if issue_filter else None,
        order_by=order_by,
    )

    # Clean and format response
    issues = [clean_issue_data(issue) for issue in issues_response["nodes"]]

    response = {
        "issues": issues,
        "total_count": len(issues),
        "search_criteria": {
            "keywords": keywords,
            "team": team,
            "status": status,
            "assignee": assignee,
            "creator": creator,
            "priority": priority,
            "labels": labels,
            "project": project,
            "created_after": created_after,
            "created_before": created_before,
            "updated_after": updated_after,
            "updated_before": updated_before,
            "sort_by": sort_by.value,
            "sort_direction": sort_direction.value,
        },
    }

    # Add pagination info
    if "pageInfo" in issues_response:
        add_pagination_info(response, issues_response["pageInfo"])

    return response


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_issue(
    context: ToolContext,
    issue_id: Annotated[
        str,
        "The Linear issue ID or identifier (e.g. 'FE-123', 'API-456') to retrieve.",
    ],
    include_comments: Annotated[
        bool, "Whether to include comments in the response. Defaults to True."
    ] = True,
    include_attachments: Annotated[
        bool, "Whether to include attachments in the response. Defaults to True."
    ] = True,
    include_relations: Annotated[
        bool,
        "Whether to include issue relations (blocks, dependencies) in the response. Defaults to True.",
    ] = True,
    include_children: Annotated[
        bool, "Whether to include sub-issues in the response. Defaults to True."
    ] = True,
) -> Annotated[dict[str, Any], "Complete issue details with related data"]:
    """Get detailed information about a specific Linear issue

    This tool retrieves complete information about a single Linear issue when you have
    its specific ID or identifier. It's purely for reading and viewing data.

    What this tool provides:
    - Complete issue details (title, description, status, assignee, etc.)
    - Comments and discussion history (if requested)
    - File attachments (if requested)
    - Related issues and dependencies (if requested)
    - Sub-issues and hierarchical relationships (if requested)

    When to use this tool:
    - When you need to examine the full details of a specific issue
    - When you want to read issue content, comments, or relationships
    - When you need to analyze or compare issue information
    - When you have an issue ID and need to understand its current state

    When NOT to use this tool:
    - Do NOT use this if you need to change, modify, or update anything
    - Do NOT use this if you're trying to create new issues
    - Do NOT use this if you're searching for multiple issues

    This tool is READ-ONLY - it cannot make any changes to issues.
    """

    client = LinearClient(context.get_auth_token_or_empty())

    # Get issue data
    issue_data = await client.get_issue_by_id(issue_id)

    if not issue_data:
        return {"error": f"Issue not found: {issue_id}"}

    # Clean and format the issue data
    cleaned_issue = clean_issue_data(issue_data)

    # Optionally remove certain fields based on parameters
    if not include_comments:
        cleaned_issue.pop("comments", None)

    if not include_attachments:
        cleaned_issue.pop("attachments", None)

    if not include_relations:
        cleaned_issue.pop("relations", None)

    if not include_children:
        cleaned_issue.pop("children", None)

    now = parse_date_string("now")
    retrieved_at = now.isoformat() if now else None

    return {
        "issue": cleaned_issue,
        "retrieved_at": retrieved_at,
    }


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["write"]))
async def update_issue(
    context: ToolContext,
    issue_id: Annotated[
        str, "The Linear issue ID or identifier (e.g. 'FE-123', 'API-456') to update."
    ],
    title: Annotated[
        str | None, "New title for the issue. Defaults to None (no change)."
    ] = None,
    description: Annotated[
        str | None, "New description for the issue. Defaults to None (no change)."
    ] = None,
    status: Annotated[
        str | None,
        "New workflow state name (e.g. 'In Progress', 'Done', 'Backlog'). Defaults to None (no change).",
    ] = None,
    assignee: Annotated[
        str | None,
        "New assignee name or email. Use 'me' for current user, 'unassigned' to remove assignee. "
        "Defaults to None (no change).",
    ] = None,
    priority: Annotated[
        str | None,
        "New priority level. Valid values: 'urgent', 'high', 'medium', 'low', 'none'. "
        "Defaults to None (no change).",
    ] = None,
    labels: Annotated[
        list[str] | None,
        "New labels for the issue. This replaces all existing labels with the provided list. "
        "AUTOMATIC CREATION: Labels that don't exist will be automatically created! "
        "To add a single label to existing labels, include both existing and new labels. "
        "Provide empty list to remove all labels. Defaults to None (no change).",
    ] = None,
    project: Annotated[
        str | None,
        "New project name or ID to assign the issue to. Use 'none' to remove from project. "
        "Defaults to None (no change).",
    ] = None,
    due_date: Annotated[
        str | None,
        "New due date for the issue. Format: YYYY-MM-DD or relative like 'next week'. "
        "Use 'none' to remove due date. Defaults to None (no change).",
    ] = None,
    cycle: Annotated[
        str | None,
        "Cycle/sprint reference to add the issue to. Supports multiple formats: "
        "'current' for current active cycle, 'next' for next upcoming cycle, "
        "'previous'/'last' for recently completed cycle, 'in 3 weeks' for cycle containing date 3 weeks from now, "
        "'next week' for cycle containing next week, or specific cycle name/number/ID. "
        "Use 'none' to remove from cycle. Defaults to None (no change).",
    ] = None,
    estimate: Annotated[
        float | None,
        "New estimate for the issue (story points or time). Use 0 to remove estimate. "
        "Defaults to None (no change).",
    ] = None,
) -> Annotated[dict[str, Any], "Updated issue data"]:
    """Update a Linear issue with new values

    This tool modifies an existing Linear issue by changing one or more of its properties.
    You must provide the issue ID, and then specify which fields you want to change.

    Important usage guidelines:
    - Call this tool ONCE with ALL the changes you want to make simultaneously
    - You can update multiple fields in a single call (e.g., priority AND assignee together)
    - Only the fields you specify will be changed; others remain untouched
    - Do NOT call this tool multiple times for the same issue - combine all changes into one call

    Special closure behavior:
    - When closing an issue (status=Done/Completed/Closed/etc.) AND providing a description,
      the description will be added as a COMMENT explaining the closure reason
    - This prevents overwriting the original issue description when documenting closure
    - Perfect for changelog-related closures: "Closed due to feature implementation in v2.1"
    - Normal description updates (without status changes) still update the description field

    Automatic workflow transitions:
    - When adding an issue to a sprint/cycle, if the issue is currently in "Backlog" status,
      it will automatically be moved to "To Do" status (unless you explicitly specify a different status)
    - Issues already in other states (In Progress, Done, etc.) will not be auto-transitioned
    - This ensures issues moved to active sprints are ready to be worked on

    When to use this tool:
    - When you need to change any property of an existing issue
    - When a user wants to modify, update, change, set, assign, or move an existing issue
    - When you have a specific issue ID and need to alter its current state
    - For status changes, priority updates, assignments, or any other modifications
    - For closing issues with explanatory comments (especially from changelog reviews)

    This tool requires an existing issue - it cannot create new issues.
    """

    client = LinearClient(context.get_auth_token_or_empty())

    # First get the current issue to determine team context
    current_issue = await client.get_issue_by_id(issue_id)
    if not current_issue:
        return {"error": f"Issue not found: {issue_id}"}

    team_id = current_issue.get("team", {}).get("id")

    # Build update input
    update_input = {}

    if title is not None:
        update_input["title"] = title

    if description is not None:
        update_input["description"] = description

    # Resolve assignee if provided
    if assignee is not None:
        if assignee.lower() == "me":
            viewer = await client.get_viewer()
            update_input["assigneeId"] = viewer["id"]
        elif assignee.lower() == "unassigned":
            update_input["assigneeId"] = None
        elif assignee.startswith("user_"):  # Assume it's an ID
            update_input["assigneeId"] = assignee
        else:
            user_data = await resolve_user_by_email_or_name(context, assignee)
            if user_data:
                update_input["assigneeId"] = user_data["id"]
            else:
                return {
                    "error": f"User not found: {assignee}. Please check the username or email and try again."
                }

    # Resolve workflow state if provided
    if status is not None:
        if status.startswith("state_"):  # Assume it's an ID
            update_input["stateId"] = status
        else:
            state_data = await resolve_workflow_state_by_name(
                context, status, team_id
            )
            if state_data:
                update_input["stateId"] = state_data["id"]
            else:
                # Status not found - provide helpful error with available statuses
                try:
                    # Get available statuses for this team to help the user
                    available_states = await client.get_workflow_states(
                        team_id=team_id
                    )
                    if available_states and available_states.get("nodes"):
                        state_names = [s["name"] for s in available_states["nodes"]]
                        return {
                            "error": f"Workflow state '{status}' not found for this team. Available statuses: {', '.join(state_names)}. You can also create a new workflow state using the 'create_workflow_state' tool if needed."
                        }
                    else:
                        return {
                            "error": f"Workflow state '{status}' not found for this team. Use 'get_workflow_states' to see available statuses or 'create_workflow_state' to create new ones."
                        }
                except Exception:
                    # Fallback if we can't get available states
                    return {
                        "error": f"Workflow state '{status}' not found for this team. Use 'get_workflow_states' to see available statuses or 'create_workflow_state' to create new ones."
                    }

    # Resolve priority if provided
    if priority is not None:
        priority_value = normalize_priority(priority)
        if priority_value is not None:
            update_input["priority"] = int(priority_value)

    # Resolve project if provided
    if project is not None:
        if project.lower() == "none":
            update_input["projectId"] = None
        elif project.startswith("project_"):  # Assume it's an ID
            update_input["projectId"] = project
        else:
            project_data = await resolve_project_by_name(context, project)
            if project_data:
                update_input["projectId"] = project_data["id"]

    # Resolve labels if provided
    if labels is not None:
        if not labels:  # Empty list - remove all labels
            update_input["labelIds"] = []
        else:
            label_data = await resolve_labels_with_autocreate(
                context, labels, team_id
            )
            update_input["labelIds"] = [label["id"] for label in label_data]

    # Handle due date
    if due_date is not None:
        if due_date.lower() == "none":
            update_input["dueDate"] = None
        else:
            validate_date_format("due_date", due_date)
            due_date_parsed = parse_date_string(due_date)
            if due_date_parsed:
                update_input["dueDate"] = due_date_parsed.date().isoformat()

    # Handle cycle/sprint with intelligent resolution
    if cycle is not None:
        if cycle.lower() == "none":
            update_input["cycleId"] = None
        elif cycle.startswith("cycle_"):  # Assume it's an ID
            update_input["cycleId"] = cycle
        else:
            # First try relative/intelligent cycle resolution
            relative_keywords = [
                "current",
                "next",
                "previous",
                "last",
                "next week",
                "next month",
            ]
            is_relative = (
                cycle.lower() in relative_keywords
                or cycle.lower().startswith("in ")
                or cycle.lower().startswith("in")
            )

            cycle_data = None
            if is_relative:
                cycle_data = await resolve_cycle_by_relative_reference(
                    context, cycle, team_id, client
                )

            # Fallback to name/number resolution if relative resolution didn't work
            if not cycle_data:
                cycle_data = await resolve_cycle_by_name(context, cycle, team_id)

            if cycle_data:
                update_input["cycleId"] = cycle_data["id"]

                # Auto-transition from Backlog to To Do when adding to a sprint
                await _auto_transition_backlog_to_todo(
                    context, current_issue, update_input, team_id, status
                )
            else:
                if is_relative:
                    return {
                        "error": f"No cycle found for '{cycle}'. This could mean no cycles are configured for the team, or no cycle matches the time period specified."
                    }
                else:
                    return {
                        "error": f"Cycle not found: {cycle}. Please check the cycle name/number and try again."
                    }

    # Handle estimate
    if estimate is not None:
        update_input["estimate"] = estimate if estimate > 0 else None

    # Remove None values
    update_input = remove_none_values(update_input)

    if not update_input:
        return {"error": "No valid fields provided for update"}

    # Handle special case: when closing an issue and providing a description,
    # add the description as a comment instead of updating the issue description
    close_reason_comment = None
    if "stateId" in update_input and description is not None and status:
        # Check if this is a completion/closure status
        closure_status_names = [
            "done",
            "completed",
            "closed",
            "resolved",
            "finished",
            "complete",
            "shipped",
            "released",
            "deployed",
            "merged",
            "fixed",
            "solved",
        ]

        is_closure_status = any(
            closure_name in status.lower() for closure_name in closure_status_names
        )

        if is_closure_status:
            # Extract the description to use as a closure comment
            close_reason_comment = description

            # Remove description from the update (don't modify the issue description)
            if "description" in update_input:
                del update_input["description"]

    # Update the issue
    result = await client.update_issue(issue_id, update_input)

    if result["success"]:
        # If we have a closure reason, add it as a comment
        if close_reason_comment:
            try:
                comment_result = await client.create_comment(
                    issue_id, close_reason_comment
                )
                if not comment_result.get("success"):
                    # Log the comment failure but don't fail the whole operation
                    pass
            except Exception:
                # Comment failed but issue update succeeded - that's okay
                pass

        # Create a helpful message based on what was updated
        message = f"Successfully updated issue {issue_id}"

        # Add context about closure comment
        if close_reason_comment:
            message += " and added closure reason as comment"

        # Add context about auto-transitions
        if "cycleId" in update_input and "stateId" in update_input and status is None:
            message += " (automatically moved from Backlog to To Do for sprint)"

        return {
            "success": True,
            "message": message,
            "issue": clean_issue_data(result["issue"]),
            "updated_fields": list(update_input.keys()),
        }
    else:
        return {
            "success": False,
            "error": "Failed to update issue",
        }


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["write"]))
async def create_issue(
    context: ToolContext,
    title: Annotated[
        str, "Title of the issue to create. Should be descriptive and concise."
    ],
    team: Annotated[
        str,
        "Team name or ID to create the issue in. REQUIRED - you must specify a team! "
        "Use 'get_teams' tool first if you need to see available teams. "
        "Examples: 'Engineering', 'Product', 'Design', 'Backend', 'Frontend'.",
    ],
    description: Annotated[
        str | None,
        "Detailed description of the issue, task, bug, or feature. Can include requirements, "
        "acceptance criteria, technical details, or any relevant context.",
    ] = None,
    assignee: Annotated[
        str | None,
        "Email address or user ID of the person to assign this issue to. Defaults to None (unassigned).",
    ] = None,
    priority: Annotated[
        str | None,
        "Priority level: 'none', 'low', 'medium', 'high', 'urgent'. Defaults to None.",
    ] = None,
    status: Annotated[
        str | None,
        "Initial workflow state (e.g. 'To Do', 'Backlog', 'In Progress'). Defaults to team's default state.",
    ] = None,
    labels: Annotated[
        list[str] | None,
        "List of label names to add to the issue (e.g. ['bug', 'critical', 'security']). "
        "AUTOMATIC CREATION: Labels that don't exist will be automatically created! "
        "Defaults to None.",
    ] = None,
    project: Annotated[
        str | None,
        "Project name or ID to associate this issue with. Defaults to None.",
    ] = None,
    parent_issue: Annotated[
        str | None, "Parent issue ID if this is a sub-issue. Defaults to None."
    ] = None,
    template: Annotated[
        str | None,
        "Template name or ID to use for creating the issue. Templates can pre-fill multiple "
        "properties and even create sub-issues automatically. When using a template, it will "
        "override some of the other parameters. Defaults to None.",
    ] = None,
    cycle: Annotated[
        str | None,
        "Cycle/sprint reference to assign the issue to. Supports multiple formats: "
        "'current' for current active cycle, 'next' for next upcoming cycle, "
        "'previous'/'last' for recently completed cycle, 'in 3 weeks' for cycle containing date 3 weeks from now, "
        "'next week' for cycle containing next week, or specific cycle name/number/ID. "
        "Defaults to None (no cycle assignment).",
    ] = None,
    due_date: Annotated[
        str | None,
        "Due date in ISO format (e.g. '2024-03-15') or relative format (e.g. 'next Friday'). Defaults to None.",
    ] = None,
    estimate: Annotated[
        int | None, "Story point estimate (1-21). Defaults to None."
    ] = None,
) -> Annotated[dict[str, Any], "Created issue details"]:
    """CREATE ISSUES, TASKS, BUGS - Primary tool for ALL work item creation

    ALWAYS USE THIS TOOL when asked to create, make, add, log, or build ANY work item

    This tool creates new Linear issues for ANY type of work including:
    Tasks and Features, Bugs and Issues, Security Vulnerabilities, User Stories

    AUTOMATIC LABEL CREATION: Labels are created automatically if they don't exist!
    You never need to check if a label exists - just specify the label names you want.
    Non-existing labels will be auto-created with appropriate colors and descriptions.

    TEMPLATE SUPPORT: Use templates to pre-fill multiple issue properties at once!
    Templates can automatically set title, description, labels, priority, assignee, and even
    create sub-issues. Just specify the template name and the tool will handle the rest.

    AUTOMATIC WORKFLOW TRANSITIONS: When creating an issue directly in a sprint/cycle,
    it will automatically be set to "To Do" status (unless you specify a different status).
    This ensures issues created in active sprints are ready to be worked on.

    IMMEDIATE ACTION REQUIRED FOR THESE REQUESTS:
    - "Create a task for implementing user profile feature" - CALL THIS TOOL NOW
    - "Create security vulnerability issue with urgent priority" - CALL THIS TOOL NOW
    - "Create a bug report for authentication system" - CALL THIS TOOL NOW
    - "Add a new feature request to the backlog" - CALL THIS TOOL NOW
    - "Create issue for API endpoint implementation" - CALL THIS TOOL NOW
    - "Create issue from test template" - CALL THIS TOOL NOW (specify template name)
    - "Log a security vulnerability" - CALL THIS TOOL NOW
    - "Make a task for database optimization" - CALL THIS TOOL NOW
    - "Create an issue labeled 'needs frontend polish'" - CALL THIS TOOL NOW
    - "Log a bug tagged as 'user complaint'" - CALL THIS TOOL NOW
    - ANY variation of create/add/make/log work items - CALL THIS TOOL NOW

    IMPORTANT: You MUST always specify a team when creating issues!
    - If user doesn't specify a team, ask them which team the issue should be created in
    - If you don't know available teams, use 'get_teams' tool first to show options
    - Never assume or default to any team name - always get user confirmation
    - Examples of good team usage: team="Engineering", team="Product", team="Design"

    Don't overthink it - just call this tool for ANY creation request, but always with a user-specified team!
    """

    client = LinearClient(context.get_auth_token_or_empty())

    # Handle parent issue first - it affects team resolution
    parent_issue_data = None
    if parent_issue:
        parent_issue_data = await resolve_issue_with_team_info(context, parent_issue)
        if not parent_issue_data:
            return {
                "error": f"Parent issue not found: {parent_issue}. Please provide a valid issue identifier."
            }

    # Resolve team with proper parent issue inheritance
    team_id = None
    if parent_issue_data:
        # For sub-issues, inherit the team from the parent issue
        team_id = parent_issue_data["team"]["id"]
        parent_team_name = parent_issue_data["team"]["name"]

        # If user specified a different team, warn but use parent's team for consistency
        if team.startswith("team_"):
            if team != team_id:
                return {
                    "error": f"Sub-issue must be created in the same team as parent issue. Parent issue {parent_issue} is in team '{parent_team_name}'. Sub-issues cannot be in different teams."
                }
        else:
            # Check if user-specified team matches parent's team
            user_team_data = await resolve_team_by_name(context, team)
            if user_team_data and user_team_data["id"] != team_id:
                return {
                    "error": f"Sub-issue must be created in the same team as parent issue. Parent issue {parent_issue} is in team '{parent_team_name}', but you specified team '{team}'. Sub-issues cannot be in different teams."
                }
    else:
        # No parent issue, resolve team normally
        if team.startswith("team_"):  # Assume it's an ID
            team_id = team
        else:
            team_data = await resolve_team_by_name(context, team)
            if team_data:
                team_id = team_data["id"]
            else:
                # Get available teams to help the user
                try:
                    client = LinearClient(context.get_auth_token_or_empty())
                    teams_response = await client.get_teams(first=20)
                    available_teams = teams_response.get("nodes", [])

                    if available_teams:
                        team_names = [
                            t["name"] for t in available_teams[:10]
                        ]  # Show up to 10 teams
                        team_list = "', '".join(team_names)
                        if len(available_teams) > 10:
                            return {
                                "error": f"Team '{team}' not found. Available teams include: '{team_list}' and {len(available_teams) - 10} others. Use 'get_teams' tool to see all teams, then specify the correct team name."
                            }
                        else:
                            return {
                                "error": f"Team '{team}' not found. Available teams: '{team_list}'. Please specify one of these existing team names."
                            }
                    else:
                        return {
                            "error": f"Team '{team}' not found and no teams could be retrieved. Please check the team name or use 'get_teams' tool to see available teams."
                        }
                except Exception:
                    return {
                        "error": f"Team '{team}' not found. Please check the team name or use 'get_teams' tool to see available teams."
                    }

    # Build create input
    create_input = {
        "title": title,
        "teamId": team_id,
    }

    if description:
        create_input["description"] = description

    # Resolve assignee if provided
    if assignee:
        if assignee.lower() == "me":
            viewer = await client.get_viewer()
            create_input["assigneeId"] = viewer["id"]
        elif assignee.startswith("user_"):  # Assume it's an ID
            create_input["assigneeId"] = assignee
        else:
            user_data = await resolve_user_by_email_or_name(context, assignee)
            if user_data:
                create_input["assigneeId"] = user_data["id"]
            else:
                return {
                    "error": f"User not found: {assignee}. Please check the username or email and try again."
                }

    # Resolve workflow state if provided
    if status:
        if status.startswith("state_"):  # Assume it's an ID
            create_input["stateId"] = status
        else:
            state_data = await resolve_workflow_state_by_name(
                context, status, team_id
            )
            if state_data:
                create_input["stateId"] = state_data["id"]
            else:
                # Status not found - provide helpful error with available statuses
                try:
                    # Get available statuses for this team to help the user
                    available_states = await client.get_workflow_states(
                        team_id=team_id
                    )
                    if available_states and available_states.get("nodes"):
                        state_names = [s["name"] for s in available_states["nodes"]]
                        return {
                            "error": f"Workflow state '{status}' not found for this team. Available statuses: {', '.join(state_names)}. You can also create a new workflow state using the 'create_workflow_state' tool if needed."
                        }
                    else:
                        return {
                            "error": f"Workflow state '{status}' not found for this team. Use 'get_workflow_states' to see available statuses or 'create_workflow_state' to create new ones."
                        }
                except Exception:
                    # Fallback if we can't get available states
                    return {
                        "error": f"Workflow state '{status}' not found for this team. Use 'get_workflow_states' to see available statuses or 'create_workflow_state' to create new ones."
                    }

    # Resolve project if provided
    if project:
        if project.startswith("project_"):  # Assume it's an ID
            create_input["projectId"] = project
        else:
            project_data = await resolve_project_by_name(context, project)
            if project_data:
                create_input["projectId"] = project_data["id"]

    # Resolve labels if provided
    if labels:
        label_data = await resolve_labels_with_autocreate(context, labels, team_id)
        create_input["labelIds"] = [label["id"] for label in label_data]

    # Resolve template if provided
    if template:
        if template.startswith("template_"):  # Assume it's an ID
            create_input["templateId"] = template
        else:
            # Resolve template by name within the team context
            template_data = await resolve_template_by_name(context, template, team_id)
            if template_data:
                create_input["templateId"] = template_data["id"]
            else:
                return {
                    "error": f"Template not found: {template}. Please check the template name and try again."
                }

    # Handle parent issue - we already resolved it earlier
    if parent_issue_data:
        create_input["parentId"] = parent_issue_data["id"]

    # Handle cycle/sprint with intelligent resolution
    if cycle:
        if cycle.startswith("cycle_"):  # Assume it's an ID
            create_input["cycleId"] = cycle
        else:
            # First try relative/intelligent cycle resolution
            relative_keywords = [
                "current",
                "next",
                "previous",
                "last",
                "next week",
                "next month",
            ]
            is_relative = (
                cycle.lower() in relative_keywords
                or cycle.lower().startswith("in ")
                or cycle.lower().startswith("in")
            )

            cycle_data = None
            if is_relative:
                cycle_data = await resolve_cycle_by_relative_reference(
                    context, cycle, team_id, client
                )

            # Fallback to name/number resolution if relative resolution didn't work
            if not cycle_data:
                cycle_data = await resolve_cycle_by_name(context, cycle, team_id)

            if cycle_data:
                create_input["cycleId"] = cycle_data["id"]

                # Auto-set to "To Do" when creating in a sprint (unless user specified status)
                if not status:
                    await _set_todo_status_for_sprint_creation(
                        context, create_input, team_id
                    )
            else:
                if is_relative:
                    return {
                        "error": f"No cycle found for '{cycle}'. This could mean no cycles are configured for the team, or no cycle matches the time period specified."
                    }
                else:
                    return {
                        "error": f"Cycle not found: {cycle}. Please check the cycle name/number and try again."
                    }

    # Handle due date
    if due_date:
        validate_date_format("due_date", due_date)
        due_date_parsed = parse_date_string(due_date)
        if due_date_parsed:
            create_input["dueDate"] = due_date_parsed.date().isoformat()

    # Handle estimate
    if estimate:
        create_input["estimate"] = estimate

    # Create the issue
    result = await client.create_issue(create_input)

    if result["success"]:
        issue_data = result["issue"]
        return {
            "success": True,
            "message": f"Successfully created issue {issue_data['identifier']}",
            "issue": clean_issue_data(issue_data),
            "issue_id": issue_data["id"],
            "issue_identifier": issue_data["identifier"],
            "url": issue_data.get("url"),
        }
    else:
        return {
            "success": False,
            "error": "Failed to create issue",
        }


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["write"]))
async def add_comment_to_issue(
    context: ToolContext,
    issue_id: Annotated[
        str,
        "The Linear issue ID or identifier (e.g. 'FE-123', 'API-456') to add a comment to.",
    ],
    comment: Annotated[
        str, "The comment text to add to the issue. Supports markdown formatting."
    ],
) -> Annotated[dict[str, Any], "Comment creation result"]:
    """Add a comment to a Linear issue

    This tool adds a comment to an existing Linear issue. Comments are useful for:
    - Documenting why an issue is being closed
    - Adding context about resolution
    - Explaining changelog-related closures
    - Providing updates on issue status

    When to use this tool:
    - When closing issues due to changelog items (document the reason)
    - When providing status updates or context
    - When explaining resolution or workarounds
    - When linking issues to external changes or releases

    The comment supports markdown formatting for better readability.
    """

    client = LinearClient(context.get_auth_token_or_empty())

    # First verify the issue exists
    current_issue = await client.get_issue_by_id(issue_id)
    if not current_issue:
        return {"error": f"Issue not found: {issue_id}"}

    # Create the comment
    result = await client.create_comment(issue_id, comment)

    if result["success"]:
        return {
            "success": True,
            "message": f"Successfully added comment to issue {issue_id}",
            "comment": result["comment"],
            "issue_id": issue_id,
        }
    else:
        return {
            "success": False,
            "error": "Failed to create comment",
        }


@tool(requires_auth=OAuth2(id="arcade-linear", scopes=["read"]))
async def get_templates(
    context: ToolContext,
    team: Annotated[
        str | None,
        "Team name or ID to filter templates by. If not provided, returns templates from all teams.",
    ] = None,
) -> Annotated[dict[str, Any], "Available issue templates"]:
    """Get available issue templates for creating structured issues

    Issue templates in Linear allow you to create issues with predefined properties including:
    - Pre-filled title, description, and labels
    - Default assignee, priority, and project assignments
    - Automatic creation of sub-issues
    - Consistent formatting and structure

    Use this tool to:
    - Discover what templates are available before creating issues
    - Find the exact template name to use with create_issue
    - See templates for a specific team or across all teams

    Templates are especially useful for:
    - Bug reports with standard fields
    - Feature requests with acceptance criteria
    - User onboarding checklists
    - Security incident response procedures
    """

    client = LinearClient(context.get_auth_token_or_empty())

    # Resolve team if provided
    team_id = None
    if team:
        if team.startswith("team_"):  # Assume it's an ID
            team_id = team
        else:
            team_data = await resolve_team_by_name(context, team)
            if team_data:
                team_id = team_data["id"]
            else:
                return {
                    "error": f"Team '{team}' not found. Please check the team name."
                }

    # Get templates
    templates_response = await client.get_templates(team_id=team_id)
    templates = templates_response.get("nodes", [])

    # Clean and format templates
    cleaned_templates = [clean_template_data(template) for template in templates]

    response = {
        "templates": cleaned_templates,
        "total_count": len(cleaned_templates),
        "team_filter": team,
    }

    if not cleaned_templates:
        if team:
            response["message"] = (
                f"No templates found for team '{team}'. Templates may not be set up for this team yet."
            )
        else:
            response["message"] = (
                "No templates found in any team. Templates may not be set up yet."
            )

    return response
