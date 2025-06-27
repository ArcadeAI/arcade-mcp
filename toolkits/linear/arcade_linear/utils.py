import re
from datetime import datetime, timedelta, timezone
from typing import Any

import dateparser
from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.client import LinearClient
from arcade_linear.constants import TIME_RANGE_MAPPINGS


def remove_none_values(data: dict[str, Any]) -> dict[str, Any]:
    """Remove None values from a dictionary"""
    return {k: v for k, v in data.items() if v is not None}


def parse_date_string(date_str: str) -> datetime | None:
    """Parse a date string into a timezone-aware datetime object using dateparser"""
    if not date_str:
        return None

    # Check if it's a relative time expression
    if date_str.lower() in TIME_RANGE_MAPPINGS:
        date_str = TIME_RANGE_MAPPINGS[date_str.lower()]

    try:
        parsed_date = dateparser.parse(date_str)
        if parsed_date is None:
            return None

        # Ensure all datetimes are timezone-aware (UTC)
        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(tzinfo=timezone.utc)

    except Exception:
        return None
    return parsed_date


def parse_date_range_for_relative_terms(
    date_str: str,
) -> tuple[datetime | None, datetime | None]:
    """Parse relative date terms into proper date ranges for filtering

    This function handles relative terms like "last week", "this month" etc. and converts
    them into proper start/end date ranges that make sense for filtering.

    Args:
        date_str: Date string like "last week", "this month", "yesterday", etc.

    Returns:
        Tuple of (start_date, end_date) where:
        - start_date: Beginning of the period
        - end_date: End of the period (None means "up to now")
    """
    if not date_str:
        return None, None

    date_str_lower = date_str.lower().strip()
    now = datetime.now(timezone.utc)

    # Handle specific relative ranges that should be treated as periods
    if date_str_lower in ["last week", "past week"]:
        # Last week means from 7 days ago to now
        start_date = now - timedelta(days=7)
        return start_date, None

    elif date_str_lower in ["this week", "current week"]:
        # This week means from beginning of week to now
        days_since_monday = now.weekday()
        start_of_week = now - timedelta(days=days_since_monday)
        start_of_week = start_of_week.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return start_of_week, None

    elif date_str_lower in ["last month", "past month"]:
        # Last month means from 30 days ago to now
        start_date = now - timedelta(days=30)
        return start_date, None

    elif date_str_lower in ["this month", "current month"]:
        # This month means from beginning of month to now
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return start_of_month, None

    elif date_str_lower in ["yesterday"]:
        # Yesterday means the previous day (full day)
        yesterday = now - timedelta(days=1)
        start_of_yesterday = yesterday.replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_of_yesterday = yesterday.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
        return start_of_yesterday, end_of_yesterday

    elif date_str_lower in ["today"]:
        # Today means from start of today to now
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_of_today, None

    elif date_str_lower in ["last year", "past year"]:
        # Last year means from 365 days ago to now
        start_date = now - timedelta(days=365)
        return start_date, None

    elif date_str_lower in ["this year", "current year"]:
        # This year means from beginning of year to now
        start_of_year = now.replace(
            month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )
        return start_of_year, None

    # If it's not a recognized relative range, treat it as a single point in time
    parsed_date = parse_date_string(date_str)
    return parsed_date, parsed_date


def is_relative_date_range_term(date_str: str) -> bool:
    """Check if a date string represents a relative range (like 'last week') vs a specific date"""
    if not date_str:
        return False

    date_str_lower = date_str.lower().strip()
    relative_range_terms = [
        "last week",
        "past week",
        "this week",
        "current week",
        "last month",
        "past month",
        "this month",
        "current month",
        "yesterday",
        "today",
        "last year",
        "past year",
        "this year",
        "current year",
    ]

    return date_str_lower in relative_range_terms


def validate_date_format(field_name: str, date_str: str | None) -> None:
    """Validate date format and raise error if invalid"""
    if not date_str:
        return

    parsed_date = parse_date_string(date_str)
    if parsed_date is None:
        raise ToolExecutionError(  # noqa: TRY003
            f"Invalid date format for {field_name}: '{date_str}'. "
            f"Please use formats like 'YYYY-MM-DD', 'today', 'last week', etc."
        )


def normalize_priority(priority: str | int | None) -> int | None:
    """Normalize priority input to Linear's integer values

    Args:
        priority: Priority as string or int

    Returns:
        Priority as integer (0=none, 1=urgent, 2=high, 3=medium, 4=low) or None

    Raises:
        ToolExecutionError: If priority is invalid
    """
    if priority is None:
        return None

    if isinstance(priority, int):
        if priority in [0, 1, 2, 3, 4]:
            return priority
        else:
            raise ToolExecutionError(  # noqa: TRY003
                f"Invalid priority value: {priority}. Must be 0-4."
            )

    priority_str = str(priority).lower().strip()
    priority_map = {
        "none": 0,
        "no priority": 0,
        "urgent": 1,
        "high": 2,
        "medium": 3,
        "low": 4,
    }

    normalized_priority = priority_map.get(priority_str)
    if normalized_priority is None:
        valid_priorities = list(priority_map.keys())
        raise ToolExecutionError(  # noqa: TRY003
            f"Invalid priority: '{priority}'. "
            f"Valid priorities are: {', '.join(valid_priorities)}"
        )

    return normalized_priority


def build_issue_filter(
    team_id: str | None = None,
    assignee_id: str | None = None,
    creator_id: str | None = None,
    state_id: str | None = None,
    priority: int | None = None,
    label_ids: list[str] | None = None,
    project_id: str | None = None,
    project_ids: list[str] | None = None,
    cycle_id: str | None = None,
    parent_id: str | None = None,
    created_at_gte: datetime | None = None,
    created_at_lte: datetime | None = None,
    updated_at_gte: datetime | None = None,
    updated_at_lte: datetime | None = None,
    completed_at_gte: datetime | None = None,
    completed_at_lte: datetime | None = None,
    due_date_gte: datetime | None = None,
    due_date_lte: datetime | None = None,
    search_query: str | None = None,
) -> dict[str, Any]:
    """Build a Linear GraphQL filter object for issues"""
    filter_obj = {}
    and_conditions = []

    if team_id:
        filter_obj["team"] = {"id": {"eq": team_id}}

    if assignee_id is not None:
        if assignee_id == "unassigned":
            # Handle unassigned issues explicitly
            filter_obj["assignee"] = {"null": True}
        else:
            # Handle specific assignee
            filter_obj["assignee"] = {"id": {"eq": assignee_id}}

    if creator_id:
        filter_obj["creator"] = {"id": {"eq": creator_id}}

    if state_id:
        filter_obj["state"] = {"id": {"eq": state_id}}

    if priority is not None:
        filter_obj["priority"] = {"eq": priority}

    if label_ids:
        if len(label_ids) == 1:
            # Single label - use simple filter
            filter_obj["labels"] = {"some": {"id": {"eq": label_ids[0]}}}
        else:
            # Multiple labels - require ALL labels (AND logic)
            # Add each label as a separate condition in the and array
            for label_id in label_ids:
                and_conditions.append({"labels": {"some": {"id": {"eq": label_id}}}})

    # Handle project filtering - support both single and multiple projects
    if project_ids:
        # Multiple projects - use 'in' operator
        filter_obj["project"] = {"id": {"in": project_ids}}
    elif project_id:
        # Single project - use 'eq' operator for backward compatibility
        filter_obj["project"] = {"id": {"eq": project_id}}

    if cycle_id:
        filter_obj["cycle"] = {"id": {"eq": cycle_id}}

    if parent_id:
        filter_obj["parent"] = {"id": {"eq": parent_id}}

    # Date filters
    if created_at_gte:
        filter_obj.setdefault("createdAt", {})["gte"] = created_at_gte.isoformat()

    if created_at_lte:
        filter_obj.setdefault("createdAt", {})["lte"] = created_at_lte.isoformat()

    if updated_at_gte:
        filter_obj.setdefault("updatedAt", {})["gte"] = updated_at_gte.isoformat()

    if updated_at_lte:
        filter_obj.setdefault("updatedAt", {})["lte"] = updated_at_lte.isoformat()

    if completed_at_gte:
        filter_obj.setdefault("completedAt", {})["gte"] = completed_at_gte.isoformat()

    if completed_at_lte:
        filter_obj.setdefault("completedAt", {})["lte"] = completed_at_lte.isoformat()

    if due_date_gte:
        filter_obj.setdefault("dueDate", {})["gte"] = due_date_gte.isoformat()

    if due_date_lte:
        filter_obj.setdefault("dueDate", {})["lte"] = due_date_lte.isoformat()

    # Text search - Enhanced keyword-based search for better matching
    if search_query:
        # Split search query into individual keywords and filter out empty strings
        keywords = [kw.strip() for kw in search_query.split() if kw.strip()]
        # Filter out very common words that don't add much value to search
        common_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "from",
            "up",
            "about",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "any",
            "both",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "so",
            "than",
            "too",
            "very",
            "can",
            "will",
            "just",
            "should",
            "now",
        }
        keywords = [
            kw for kw in keywords if kw.lower() not in common_words and len(kw) >= 2
        ]

        if len(keywords) == 0:
            # No meaningful keywords after filtering - use original search
            filter_obj["or"] = [
                {"title": {"containsIgnoreCase": search_query}},
                {"description": {"containsIgnoreCase": search_query}},
                {"labels": {"some": {"name": {"containsIgnoreCase": search_query}}}},
            ]
        elif len(keywords) == 1:
            # Single keyword - search broadly in title, description, and labels
            filter_obj["or"] = [
                {"title": {"containsIgnoreCase": keywords[0]}},
                {"description": {"containsIgnoreCase": keywords[0]}},
                {"labels": {"some": {"name": {"containsIgnoreCase": keywords[0]}}}},
            ]
        else:
            # Multiple keywords - use a flexible approach that finds issues containing multiple keywords
            # This creates better matches by looking for issues that contain several keywords

            # Create individual keyword conditions for title, description, and labels
            title_conditions = [
                {"title": {"containsIgnoreCase": keyword}} for keyword in keywords
            ]
            desc_conditions = [
                {"description": {"containsIgnoreCase": keyword}}
                for keyword in keywords
            ]
            label_conditions = [
                {"labels": {"some": {"name": {"containsIgnoreCase": keyword}}}}
                for keyword in keywords
            ]

            # Strategy: Look for issues where:
            # 1. Title contains multiple keywords (most relevant), OR
            # 2. Title contains at least one keyword AND description contains at least one keyword, OR
            # 3. Any field contains at least one keyword (broader fallback)

            multi_keyword_conditions = []

            # High relevance: Multiple keywords in title
            if len(keywords) >= 2:
                # For 2+ keywords, look for issues with at least 2 keywords in title
                for i, kw1 in enumerate(keywords):
                    for kw2 in keywords[i + 1 :]:
                        multi_keyword_conditions.append({
                            "and": [
                                {"title": {"containsIgnoreCase": kw1}},
                                {"title": {"containsIgnoreCase": kw2}},
                            ]
                        })

            # Medium relevance: One keyword in title AND one in description
            for title_kw in keywords:
                for desc_kw in keywords:
                    if title_kw != desc_kw:  # Different keywords
                        multi_keyword_conditions.append({
                            "and": [
                                {"title": {"containsIgnoreCase": title_kw}},
                                {"description": {"containsIgnoreCase": desc_kw}},
                            ]
                        })

            # Lower relevance: Single keyword matches (fallback)
            single_keyword_conditions = (
                title_conditions + desc_conditions + label_conditions
            )

            # Combine all conditions with preference for multi-keyword matches
            all_conditions = multi_keyword_conditions + single_keyword_conditions
            filter_obj["or"] = all_conditions

    # If we have AND conditions (like multiple labels), add them to the filter
    if and_conditions:
        if "and" in filter_obj:
            # Extend existing and conditions
            filter_obj["and"].extend(and_conditions)
        else:
            # Create new and conditions
            filter_obj["and"] = and_conditions

    return filter_obj


async def resolve_issue_identifier_to_uuid(
    context: ToolContext, issue_identifier: str
) -> str | None:
    """Resolve an issue identifier like 'TES-17' to its UUID

    Args:
        context: Tool context with authentication
        issue_identifier: Issue identifier like 'TES-17', 'API-123', etc.

    Returns:
        UUID string if found, None otherwise
    """
    if not issue_identifier:
        return None

    # If it's already a UUID (36 chars with dashes), return as-is
    if len(issue_identifier) == 36 and issue_identifier.count("-") == 4:
        return issue_identifier

    client = LinearClient(context.get_auth_token_or_empty())

    # Query the issue directly by identifier - Linear supports this approach
    query = """
    query GetIssueByIdentifier($id: String!) {
        issue(id: $id) {
            id
            identifier
            title
            team {
                id
                key
                name
            }
        }
    }
    """

    try:
        variables = {"id": issue_identifier}
        result = await client.execute_query(query, variables)
        issue = result["data"]["issue"]

        if issue:
            return issue["id"]
    except Exception:
        # If the direct query fails, the issue doesn't exist
        pass

    return None


async def resolve_issue_with_team_info(
    context: ToolContext, issue_identifier: str
) -> dict[str, Any] | None:
    """Resolve an issue identifier and return full issue info including team data

    This is used when we need both the issue UUID and team information,
    such as when creating sub-issues that should inherit the parent's team.

    Args:
        context: Tool context with authentication
        issue_identifier: Issue identifier like 'TES-17', 'API-123', etc.

    Returns:
        Issue data dictionary with team info if found, None otherwise
    """
    if not issue_identifier:
        return None

    client = LinearClient(context.get_auth_token_or_empty())

    # Query the issue directly by identifier
    query = """
    query GetIssueWithTeam($id: String!) {
        issue(id: $id) {
            id
            identifier
            title
            team {
                id
                key
                name
            }
        }
    }
    """

    try:
        variables = {"id": issue_identifier}
        result = await client.execute_query(query, variables)
        issue = result["data"]["issue"]

        if issue:
            return issue
    except Exception:
        return None

    return None


async def get_default_team_fallback(context: ToolContext) -> dict[str, Any] | None:
    """Get a safe default team to use as fallback when no team is specified

    This function finds the first available team to use as a fallback instead of
    hardcoding "Frontend" which may not exist.

    Args:
        context: Tool context with authentication

    Returns:
        Team data dictionary if found, None otherwise
    """
    client = LinearClient(context.get_auth_token_or_empty())

    try:
        teams_response = await client.get_teams(first=10)
        teams = teams_response.get("nodes", [])

        if teams:
            # Return the first team as a safe fallback
            return teams[0]
    except Exception:
        return None

    return None


async def resolve_team_by_name(
    context: ToolContext, team_name: str
) -> dict[str, Any] | None:
    """Resolve a team name to team data"""
    client = LinearClient(context.get_auth_token_or_empty())

    # Get teams and filter by name
    teams_response = await client.get_teams(name_filter=team_name)
    teams = teams_response.get("nodes", [])

    # Look for exact match first
    exact_matches = [
        team for team in teams if team["name"].lower() == team_name.lower()
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        team_names = [team["name"] for team in exact_matches]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple teams found with name '{team_name}': {', '.join(team_names)}. "
            f"Please specify the team more precisely."
        )

    # Look for partial matches
    partial_matches = [
        team for team in teams if team_name.lower() in team["name"].lower()
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]
    elif len(partial_matches) > 1:
        team_names = [team["name"] for team in partial_matches]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple teams found containing '{team_name}': {', '.join(team_names)}. "
            f"Please specify the team more precisely."
        )

    return None


async def resolve_user_by_email_or_name(
    context: ToolContext, identifier: str
) -> dict[str, Any] | None:
    """Resolve a user by email or name"""
    client = LinearClient(context.get_auth_token_or_empty())

    # Query to search users
    query = """
    query SearchUsers($filter: UserFilter) {
        users(filter: $filter) {
            nodes {
                id
                name
                email
                displayName
                avatarUrl
                active
            }
        }
    }
    """

    # Try email first
    if "@" in identifier:
        variables = {"filter": {"email": {"eq": identifier}}}
        result = await client.execute_query(query, variables)
        users = result["data"]["users"]["nodes"]
        if users:
            return users[0]

    # Try by name
    variables = {"filter": {"name": {"containsIgnoreCase": identifier}}}
    result = await client.execute_query(query, variables)
    users = result["data"]["users"]["nodes"]

    if not users:
        return None

    # Look for exact match
    exact_matches = [
        user for user in users if user["name"].lower() == identifier.lower()
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        user_names = [user["name"] for user in exact_matches]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple users found with name '{identifier}': {', '.join(user_names)}. "
            f"Please specify the user more precisely."
        )

    # Look for partial matches
    if len(users) == 1:
        return users[0]
    elif len(users) > 1:
        user_names = [user["name"] for user in users]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple users found containing '{identifier}': {', '.join(user_names)}. "
            f"Please specify the user more precisely."
        )

    return None


async def resolve_workflow_state_by_name(
    context: ToolContext, state_name: str, team_id: str | None = None
) -> dict[str, Any] | None:
    """Resolve a workflow state by name"""
    client = LinearClient(context.get_auth_token_or_empty())

    # Query to get workflow states
    query = """
    query GetWorkflowStates($filter: WorkflowStateFilter) {
        workflowStates(filter: $filter) {
            nodes {
                id
                name
                type
                color
                position
                team {
                    id
                    key
                    name
                }
            }
        }
    }
    """

    # Build filter
    filter_obj = {"name": {"containsIgnoreCase": state_name}}
    if team_id:
        filter_obj["team"] = {"id": {"eq": team_id}}

    variables = {"filter": filter_obj}
    result = await client.execute_query(query, variables)
    states = result["data"]["workflowStates"]["nodes"]

    if not states:
        return None

    # Look for exact match
    exact_matches = [
        state for state in states if state["name"].lower() == state_name.lower()
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    elif len(exact_matches) > 1:
        state_names = [
            f"{state['name']} ({state['team']['name']})" for state in exact_matches
        ]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple workflow states found with name '{state_name}': "
            f"{', '.join(state_names)}. Please specify the state more precisely."
        )

    # Look for partial matches
    if len(states) == 1:
        return states[0]
    elif len(states) > 1:
        state_names = [
            f"{state['name']} ({state['team']['name']})" for state in states
        ]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple workflow states found containing '{state_name}': "
            f"{', '.join(state_names)}. Please specify the state more precisely."
        )

    return None


async def resolve_project_by_name(
    context: ToolContext, project_name: str
) -> dict[str, Any] | None:
    """Resolve a project by name with fuzzy matching support

    Args:
        context: Tool context with authentication
        project_name: Name of the project to find

    Returns:
        Project data dictionary if found, None otherwise
    """
    if not project_name:
        return None

    client = LinearClient(context.get_auth_token_or_empty())
    projects_response = await client.get_projects()
    projects = projects_response.get("nodes", [])

    # First try exact match (case insensitive)
    for project in projects:
        if project.get("name", "").lower() == project_name.lower():
            return clean_project_data(project)

    # Then try partial match
    for project in projects:
        if project_name.lower() in project.get("name", "").lower():
            return clean_project_data(project)

    return None


async def resolve_projects_by_name(
    context: ToolContext, project_name: str
) -> list[dict[str, Any]]:
    """Resolve ALL projects by name with fuzzy matching support

    This function returns ALL projects that match the given name, which is critical
    for search operations where multiple projects may have the same name across different teams.

    Args:
        context: Tool context with authentication
        project_name: Name of the project(s) to find

    Returns:
        List of project data dictionaries. Empty list if none found.
    """
    if not project_name:
        return []

    client = LinearClient(context.get_auth_token_or_empty())
    projects_response = await client.get_projects()
    projects = projects_response.get("nodes", [])

    # First collect exact matches (case insensitive)
    exact_matches = []
    for project in projects:
        if project.get("name", "").lower() == project_name.lower():
            exact_matches.append(clean_project_data(project))

    if exact_matches:
        return exact_matches

    # If no exact matches, try matching with common variations
    # Handle space/hyphen/underscore variations for more flexible matching
    normalized_search = project_name.lower().replace(" ", "-").replace("_", "-")
    space_to_underscore = project_name.lower().replace(" ", "_")

    variation_matches = []
    for project in projects:
        project_name_lower = project.get("name", "").lower()
        normalized_project = project_name_lower.replace(" ", "-").replace("_", "-")

        # Try normalized matching (spaces -> hyphens)
        if (
            normalized_project == normalized_search
            or project_name_lower == space_to_underscore
        ):
            variation_matches.append(clean_project_data(project))

    if variation_matches:
        return variation_matches

    # Only then try partial matches - but be more restrictive
    partial_matches = []
    for project in projects:
        project_name_lower = project.get("name", "").lower()
        search_lower = project_name.lower()

        # Only match if the search term is a significant part of the project name
        # and the project name isn't too much longer (to avoid overly broad matches)
        if (
            search_lower in project_name_lower
            and len(search_lower) >= 3  # Minimum 3 characters for partial match
            and len(project_name_lower) <= len(search_lower) * 2
        ):  # Project name not more than 2x longer
            partial_matches.append(clean_project_data(project))

    return partial_matches


async def resolve_cycle_by_name(
    context: ToolContext, cycle_name: str, team: str | None = None
) -> dict[str, Any] | None:
    """Resolve a cycle by name with fuzzy matching support

    Args:
        context: Tool context with authentication
        cycle_name: Name of the cycle to find
        team: Optional team name to filter cycles

    Returns:
        Cycle data dictionary if found, None otherwise
    """
    if not cycle_name:
        return None

    client = LinearClient(context.get_auth_token_or_empty())

    # Get team ID if team name provided
    team_id = None
    if team:
        team_data = await resolve_team_by_name(context, team)
        if team_data:
            team_id = team_data["id"]

    cycles_response = await client.get_cycles(team_id=team_id)
    cycles = cycles_response.get("nodes", [])

    # First try to match by cycle number if the input is numeric
    if cycle_name.isdigit():
        cycle_number = int(cycle_name)
        for cycle in cycles:
            if cycle.get("number") == cycle_number:
                return clean_cycle_data(cycle)

    # Then try exact match by name (case insensitive)
    for cycle in cycles:
        cycle_name_field = cycle.get("name")
        if cycle_name_field and cycle_name_field.lower() == cycle_name.lower():
            return clean_cycle_data(cycle)

    # Then try partial match by name
    for cycle in cycles:
        cycle_name_field = cycle.get("name")
        if cycle_name_field and cycle_name.lower() in cycle_name_field.lower():
            return clean_cycle_data(cycle)

    return None


async def resolve_cycle_by_relative_reference(
    context: ToolContext,
    cycle_reference: str,
    team_id: str,
    client: LinearClient | None = None,
) -> dict[str, Any] | None:
    """Resolve cycles by relative references like 'current', 'next', 'previous', or date-based like 'in 3 weeks'

    This function handles intelligent cycle resolution for common AI agent use cases:
    - 'current' -> currently active cycle
    - 'next' -> next upcoming cycle after current
    - 'previous' or 'last' -> most recently completed cycle
    - 'in X weeks/days' -> cycle that contains a date X time from now
    - 'next week' -> cycle that contains next week

    Args:
        context: Tool context with authentication
        cycle_reference: The relative reference to resolve
        team_id: Team ID to scope the search

    Returns:
        Cycle data dictionary if found, None otherwise
    """
    if not cycle_reference or not team_id:
        return None

    from datetime import datetime, timedelta, timezone

    if client is None:
        client = LinearClient(context.get_auth_token_or_empty())
    cycle_ref_lower = cycle_reference.lower().strip()

    # Handle simple relative references
    if cycle_ref_lower == "current":
        return await client.get_current_cycle(team_id)

    # Get all cycles for the team to work with
    cycles_response = await client.get_cycles(
        team_id=team_id, active_only=False, include_completed=True
    )
    cycles = cycles_response.get("nodes", [])

    if not cycles:
        return None

    # Sort cycles by start date for easier relative navigation
    def parse_cycle_date(cycle):
        starts_at = cycle.get("startsAt")
        if starts_at:
            try:
                # Ensure we parse with timezone info
                if starts_at.endswith("Z"):
                    # Replace Z with +00:00 for UTC timezone
                    return datetime.fromisoformat(starts_at.replace("Z", "+00:00"))
                else:
                    # Try to parse as-is (might already have timezone info)
                    parsed = datetime.fromisoformat(starts_at)
                    # If it's naive, assume UTC
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    return parsed
            except (ValueError, AttributeError):
                return None
        return None

    cycles_with_dates = [
        (cycle, parse_cycle_date(cycle))
        for cycle in cycles
        if parse_cycle_date(cycle) is not None
    ]
    cycles_with_dates.sort(key=lambda x: x[1])  # Sort by date

    # Use timezone-aware datetime to match Linear's ISO dates
    now = datetime.now(timezone.utc)

    # Handle 'next' - find next cycle after current
    if cycle_ref_lower == "next":
        # Find current cycle first
        current_cycle = await client.get_current_cycle(team_id)
        if current_cycle:
            current_starts = parse_cycle_date(current_cycle)
            if current_starts:
                # Find the next cycle after current
                for cycle, start_date in cycles_with_dates:
                    if start_date > current_starts:
                        return clean_cycle_data(cycle)
        else:
            # No current cycle, find next upcoming cycle
            for cycle, start_date in cycles_with_dates:
                if start_date > now:
                    return clean_cycle_data(cycle)
        return None

    # Handle 'previous' or 'last' - find most recently completed cycle
    if cycle_ref_lower in ["previous", "last"]:
        # Find cycles that have completed
        for cycle, start_date in reversed(cycles_with_dates):
            if cycle.get("completedAt") and start_date < now:
                return clean_cycle_data(cycle)
        return None

    # Handle date-based references like "in 3 weeks", "in 2 days", "next week"
    target_date = None

    # Pattern for "in X weeks/days/months"
    in_pattern = re.match(
        r"in\s+(\d+)\s+(week|weeks|day|days|month|months)", cycle_ref_lower
    )
    if in_pattern:
        amount = int(in_pattern.group(1))
        unit = in_pattern.group(2)

        if unit.startswith("week"):
            target_date = now + timedelta(weeks=amount)
        elif unit.startswith("day"):
            target_date = now + timedelta(days=amount)
        elif unit.startswith("month"):
            target_date = now + timedelta(days=amount * 30)  # Approximate

    # Handle "next week"
    elif cycle_ref_lower == "next week":
        target_date = now + timedelta(weeks=1)

    # Handle "next month"
    elif cycle_ref_lower == "next month":
        target_date = now + timedelta(days=30)

    # If we have a target date, find the cycle that contains it
    if target_date:
        for cycle, start_date in cycles_with_dates:
            ends_at = cycle.get("endsAt")
            if ends_at:
                try:
                    # Parse end date with timezone info
                    if ends_at.endswith("Z"):
                        end_date = datetime.fromisoformat(
                            ends_at.replace("Z", "+00:00")
                        )
                    else:
                        parsed = datetime.fromisoformat(ends_at)
                        if parsed.tzinfo is None:
                            parsed = parsed.replace(tzinfo=timezone.utc)
                        end_date = parsed

                    # Check if target date falls within this cycle
                    if start_date <= target_date <= end_date:
                        return clean_cycle_data(cycle)
                except (ValueError, AttributeError):
                    continue

    return None


async def resolve_labels_by_names(
    context: ToolContext, label_names: list[str]
) -> list[dict[str, Any]]:
    """Resolve label names to label data"""
    if not label_names:
        return []

    client = LinearClient(context.get_auth_token_or_empty())

    # Query to search labels
    query = """
    query SearchLabels($filter: IssueLabelFilter) {
        issueLabels(filter: $filter) {
            nodes {
                id
                name
                color
                description
            }
        }
    }
    """

    resolved_labels = []

    for label_name in label_names:
        variables = {"filter": {"name": {"containsIgnoreCase": label_name}}}
        result = await client.execute_query(query, variables)
        labels = result["data"]["issueLabels"]["nodes"]

        if not labels:
            raise ToolExecutionError(f"Label '{label_name}' not found.")  # noqa: TRY003

        # Look for exact match
        exact_matches = [
            label for label in labels if label["name"].lower() == label_name.lower()
        ]
        if len(exact_matches) == 1:
            resolved_labels.append(exact_matches[0])
        elif len(exact_matches) > 1:
            label_names_list = [label["name"] for label in exact_matches]
            raise ToolExecutionError(  # noqa: TRY003
                f"Multiple labels found with name '{label_name}': "
                f"{', '.join(label_names_list)}. Please specify the label"
                "more precisely."
            )
        else:
            # Look for partial matches
            if len(labels) == 1:
                resolved_labels.append(labels[0])
            elif len(labels) > 1:
                label_names_list = [label["name"] for label in labels]
                raise ToolExecutionError(  # noqa: TRY003
                    f"Multiple labels found containing '{label_name}': "
                    f"{', '.join(label_names_list)}. Please specify the label"
                    "more precisely."
                )

    return resolved_labels


async def resolve_labels_with_autocreate(  # noqa: C901
    context: ToolContext, label_names: list[str], team_id: str | None = None
) -> list[dict[str, Any]]:
    """Resolve label names to label data, automatically creating team-specific labels.

    This function implements team-aware label resolution:
    1. Check if labels exist for the specific team first
    2. If label exists for team or is workspace-global, use it
    3. If label exists but for different team, create new one for current team
    4. If label doesn't exist at all, create it for the team
    5. Handle race conditions and duplicate creation gracefully

    Args:
        context: Tool context with authentication
        label_names: List of label names to resolve/create
        team_id: Team ID to scope label lookup and creation

    Returns:
        List of label data dictionaries compatible with the specified team
    """
    if not label_names:
        return []

    client = LinearClient(context.get_auth_token_or_empty())

    # Get all existing labels to understand what's available
    all_labels_response = await client.get_labels()
    all_labels = all_labels_response.get("nodes", [])

    # Organize labels by name and team
    labels_by_name = {}
    for label in all_labels:
        name_lower = label["name"].lower()
        if name_lower not in labels_by_name:
            labels_by_name[name_lower] = []
        labels_by_name[name_lower].append(label)

    resolved_labels = []

    for label_name in label_names:
        label_name_lower = label_name.lower()

        if label_name_lower in labels_by_name:
            # Label name exists, find the best match
            existing_labels = labels_by_name[label_name_lower]

            # First priority: Label for the specific team
            team_label = None
            workspace_label = None

            for label in existing_labels:
                label_team_id = (
                    label.get("team", {}).get("id") if label.get("team") else None
                )
                if label_team_id == team_id:
                    team_label = label
                    break
                elif label_team_id is None:
                    # Workspace-global label (no team assignment)
                    workspace_label = label

            if team_label:
                # Perfect match: label exists for this team
                resolved_labels.append(team_label)
            elif workspace_label:
                # Good match: workspace-global label (should work for any team)
                resolved_labels.append(workspace_label)
            else:
                # Label exists but only for other teams - create team-specific version
                await _create_team_specific_label(
                    client, label_name, team_id, resolved_labels, label_name_lower
                )
        else:
            # Label doesn't exist at all - create it for the team
            await _create_team_specific_label(
                client, label_name, team_id, resolved_labels, label_name_lower
            )

    return resolved_labels


async def _auto_transition_backlog_to_todo(  # noqa: C901
    context: ToolContext,
    current_issue: dict[str, Any],
    update_input: dict[str, Any],
    team_id: str,
    user_provided_status: str | None,
) -> None:
    """Auto-transition issue from Backlog to To Do when adding to a sprint

    This function implements the workflow rule: when an issue is moved from
    backlog to an active sprint, it should automatically transition to "To Do"
    status unless the user explicitly provided a different status or the issue
    is already in a non-backlog state.

    Args:
        context: Tool context with authentication
        current_issue: The current issue data
        update_input: The update input dict to modify
        team_id: Team ID for resolving workflow states
        user_provided_status: Status explicitly provided by user (if any)
    """
    # Don't auto-transition if user explicitly provided a status
    if user_provided_status is not None:
        return

    # Don't auto-transition if user already set a stateId in this update
    if "stateId" in update_input:
        return

    # Get current issue state
    current_state = current_issue.get("state")
    if not current_state:
        return

    current_state_name = current_state.get("name", "").lower()
    current_state_type = current_state.get("type", "").lower()

    # Check if current state is a backlog state
    backlog_state_names = ["backlog", "triage", "new", "untriaged", "icebox"]
    backlog_state_types = ["backlog", "unstarted"]

    is_backlog_state = (
        current_state_name in backlog_state_names
        or current_state_type in backlog_state_types
        or any(
            backlog_name in current_state_name for backlog_name in backlog_state_names
        )
    )

    if not is_backlog_state:
        # Issue is not in backlog, don't auto-transition
        return

    # Find "To Do" state for this team
    try:
        from arcade_linear.client import LinearClient

        client = LinearClient(context.get_auth_token_or_empty())
        workflow_states = await client.get_workflow_states(team_id=team_id)

        if not workflow_states or not workflow_states.get("nodes"):
            return

        # Look for "To Do" or similar states
        todo_state_names = [
            "to do",
            "todo",
            "ready",
            "ready for dev",
            "ready to start",
            "open",
        ]
        todo_state = None

        for state in workflow_states["nodes"]:
            state_name = state.get("name", "").lower()
            state_type = state.get("type", "").lower()

            # Look for exact matches first
            if state_name in todo_state_names:
                todo_state = state
                break

            # Look for "started" type states (which usually includes To Do)
            if state_type == "started" and any(
                name in state_name for name in todo_state_names
            ):
                todo_state = state
                break

        # Fallback: look for any "started" type state if no exact match
        if not todo_state:
            for state in workflow_states["nodes"]:
                if state.get("type", "").lower() == "started":
                    todo_state = state
                    break

        if todo_state:
            # Add the state transition to the update
            update_input["stateId"] = todo_state["id"]

    except Exception:
        # If we can't find or set the To Do state, that's okay -
        # the cycle assignment will still work
        pass


async def _set_todo_status_for_sprint_creation(
    context: ToolContext, create_input: dict[str, Any], team_id: str
) -> None:
    """Set "To Do" status when creating an issue directly in a sprint

    When creating an issue directly in a sprint (rather than backlog),
    it should default to "To Do" status to indicate it's ready to work on.

    Args:
        context: Tool context with authentication
        create_input: The create input dict to modify
        team_id: Team ID for resolving workflow states
    """
    # Don't override if stateId is already set
    if "stateId" in create_input:
        return

    try:
        from arcade_linear.client import LinearClient

        client = LinearClient(context.get_auth_token_or_empty())
        workflow_states = await client.get_workflow_states(team_id=team_id)

        if not workflow_states or not workflow_states.get("nodes"):
            return

        # Look for "To Do" or similar states (same logic as auto-transition)
        todo_state_names = [
            "to do",
            "todo",
            "ready",
            "ready for dev",
            "ready to start",
            "open",
        ]
        todo_state = None

        for state in workflow_states["nodes"]:
            state_name = state.get("name", "").lower()
            state_type = state.get("type", "").lower()

            # Look for exact matches first
            if state_name in todo_state_names:
                todo_state = state
                break

            # Look for "started" type states
            if state_type == "started" and any(
                name in state_name for name in todo_state_names
            ):
                todo_state = state
                break

        # Fallback: look for any "started" type state
        if not todo_state:
            for state in workflow_states["nodes"]:
                if state.get("type", "").lower() == "started":
                    todo_state = state
                    break

        if todo_state:
            create_input["stateId"] = todo_state["id"]

    except Exception:
        # If we can't set the To Do state, that's okay - issue will use team default
        pass


async def _create_team_specific_label(
    client: LinearClient,
    label_name: str,
    team_id: str | None,
    resolved_labels: list[dict[str, Any]],
    label_name_lower: str,
) -> None:
    """Helper function to create a team-specific label"""
    try:
        # Generate a nice default color for new labels
        default_colors = [
            "#3b82f6",  # Blue
            "#10b981",  # Green
            "#f59e0b",  # Amber
            "#ef4444",  # Red
            "#8b5cf6",  # Purple
            "#f97316",  # Orange
            "#06b6d4",  # Cyan
            "#84cc16",  # Lime
        ]

        # Use a simple hash to pick a consistent color for this label name
        color_index = hash(label_name) % len(default_colors)
        default_color = default_colors[color_index]

        create_result = await client.create_label(
            name=label_name,  # Use original case for creation
            team_id=team_id,
            color=default_color,
            description=f"Auto-created team-specific label for {label_name}",
        )

        if create_result.get("success") and create_result.get("label"):
            resolved_labels.append(create_result["label"])
        else:
            # If creation failed, raise an error
            raise ToolExecutionError(
                f"Failed to create label '{label_name}' for team"
            )

    except Exception as e:
        # Check if the error is due to duplicate label name
        error_message = str(e).lower()
        if "duplicate" in error_message or "already exists" in error_message:
            # Label was created between our check and creation attempt (race condition)
            # Re-fetch labels and find the team-specific one
            try:
                updated_labels_response = await client.get_labels(team_id=team_id)
                updated_labels = updated_labels_response.get("nodes", [])

                # Look for the label we were trying to create
                for label in updated_labels:
                    if label["name"].lower() == label_name_lower:
                        resolved_labels.append(label)
                        return

                # If still not found, try global lookup
                all_updated_labels_response = await client.get_labels()
                all_updated_labels = all_updated_labels_response.get("nodes", [])

                for label in all_updated_labels:
                    if label["name"].lower() == label_name_lower and (
                        not label.get("team")
                        or label.get("team", {}).get("id") == team_id
                    ):
                        resolved_labels.append(label)
                        return

                # Still can't find it, this shouldn't happen
                raise ToolExecutionError(
                    f"Label '{label_name}' was reported as duplicate but cannot be found for team."
                )
            except Exception:
                # If we can't fetch labels again, provide a helpful error
                raise ToolExecutionError(
                    f"Label '{label_name}' may already exist but could not be retrieved. Please try again."
                )
        else:
            # Other error, re-raise with original message
            raise ToolExecutionError(
                f"Failed to create label '{label_name}' for team: {e!s}"
            )


async def resolve_labels_read_only(
    context: ToolContext, label_names: list[str], team_id: str | None = None
) -> list[dict[str, Any]]:
    """Resolve label names to existing label data for read-only operations like search

    This function is used for search operations where we should not create labels.
    It requires ALL requested labels to exist to ensure accurate filtering.

    Args:
        context: Tool context with authentication
        label_names: List of label names to resolve
        team_id: Optional team ID to scope label lookup

    Returns:
        List of existing label data dictionaries. Raises error if any label is missing.
    """
    if not label_names:
        return []

    client = LinearClient(context.get_auth_token_or_empty())

    # Get ALL labels (both team-specific and global) to ensure we find workspace labels
    all_labels_response = await client.get_labels()
    all_labels = all_labels_response.get("nodes", [])

    # Filter labels to those available for this team context
    # Include: team-specific labels for this team + global labels (no team assignment)
    available_labels = []
    for label in all_labels:
        label_team_id = label.get("team", {}).get("id") if label.get("team") else None
        if label_team_id == team_id or label_team_id is None:
            # Label is either for this specific team or is a global/workspace label
            available_labels.append(label)

    # Create a mapping of label names to label objects (case-insensitive)
    available_labels_map = {
        label["name"].lower(): label for label in available_labels
    }

    resolved_labels = []
    missing_labels = []

    for label_name in label_names:
        label_name_lower = label_name.lower()

        if label_name_lower in available_labels_map:
            # Label exists, add it to results
            resolved_labels.append(available_labels_map[label_name_lower])
        else:
            # Track missing labels for error reporting
            missing_labels.append(label_name)

    # If any labels are missing, provide a helpful error
    if missing_labels:
        available_label_names = [
            label["name"] for label in available_labels[:10]
        ]  # Show up to 10 available labels
        if team_id:
            team_info = "in this team"
        else:
            team_info = "in the workspace"

        if len(missing_labels) == 1:
            error_msg = f"Label '{missing_labels[0]}' not found {team_info}."
        else:
            missing_list = "', '".join(missing_labels)
            error_msg = f"Labels '{missing_list}' not found {team_info}."

        if available_label_names:
            available_list = "', '".join(available_label_names)
            if len(available_labels) > 10:
                error_msg += f" Available labels include: '{available_list}' and {len(available_labels) - 10} others."
            else:
                error_msg += f" Available labels: '{available_list}'."
        else:
            error_msg += " No labels are available in this scope."

        raise ToolExecutionError(error_msg)

    return resolved_labels


def clean_issue_data(issue_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format issue data for consistent output"""
    if not issue_data:
        return {}

    cleaned = {
        "id": issue_data.get("id"),
        "identifier": issue_data.get("identifier"),
        "title": issue_data.get("title"),
        "description": issue_data.get("description"),
        "priority": issue_data.get("priority"),
        "priority_label": issue_data.get("priorityLabel"),
        "estimate": issue_data.get("estimate"),
        "created_at": issue_data.get("createdAt"),
        "updated_at": issue_data.get("updatedAt"),
        "completed_at": issue_data.get("completedAt"),
        "due_date": issue_data.get("dueDate"),
        "url": issue_data.get("url"),
        "branch_name": issue_data.get("branchName"),
    }

    # Clean nested objects
    if issue_data.get("creator"):
        cleaned["creator"] = clean_user_data(issue_data["creator"])

    if issue_data.get("assignee"):
        cleaned["assignee"] = clean_user_data(issue_data["assignee"])

    if issue_data.get("state"):
        cleaned["state"] = clean_state_data(issue_data["state"])

    if issue_data.get("team"):
        cleaned["team"] = clean_team_data(issue_data["team"])

    if issue_data.get("project"):
        cleaned["project"] = clean_project_data(issue_data["project"])

    if issue_data.get("labels") and issue_data["labels"].get("nodes"):
        cleaned["labels"] = [
            clean_label_data(label) for label in issue_data["labels"]["nodes"]
        ]

    if issue_data.get("children") and issue_data["children"].get("nodes"):
        cleaned["children"] = [
            clean_issue_data(child) for child in issue_data["children"]["nodes"]
        ]

    if issue_data.get("parent"):
        cleaned["parent"] = clean_issue_data(issue_data["parent"])

    # Handle issue relations (dependencies, blockers, etc.)
    if issue_data.get("relations") and issue_data["relations"].get("nodes"):
        cleaned["relations"] = [
            clean_relation_data(relation)
            for relation in issue_data["relations"]["nodes"]
        ]

    # Handle comments if present
    if issue_data.get("comments") and issue_data["comments"].get("nodes"):
        cleaned["comments"] = [
            clean_comment_data(comment) for comment in issue_data["comments"]["nodes"]
        ]

    # Handle attachments if present
    if issue_data.get("attachments") and issue_data["attachments"].get("nodes"):
        cleaned["attachments"] = [
            clean_attachment_data(attachment)
            for attachment in issue_data["attachments"]["nodes"]
        ]

    return remove_none_values(cleaned)


def clean_user_data(user_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format user data"""
    if not user_data:
        return {}

    return remove_none_values({
        "id": user_data.get("id"),
        "name": user_data.get("name"),
        "email": user_data.get("email"),
        "display_name": user_data.get("displayName"),
        "avatar_url": user_data.get("avatarUrl"),
    })


def clean_team_data(team_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format team data"""
    if not team_data:
        return {}

    cleaned = {
        "id": team_data.get("id"),
        "key": team_data.get("key"),
        "name": team_data.get("name"),
        "description": team_data.get("description"),
        "private": team_data.get("private"),
        "archived_at": team_data.get("archivedAt"),
        "created_at": team_data.get("createdAt"),
        "updated_at": team_data.get("updatedAt"),
        "icon": team_data.get("icon"),
        "color": team_data.get("color"),
    }

    if team_data.get("members") and team_data["members"].get("nodes"):
        cleaned["members"] = [
            clean_user_data(member) for member in team_data["members"]["nodes"]
        ]

    return remove_none_values(cleaned)


def clean_state_data(state_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format workflow state data"""
    if not state_data:
        return {}

    return remove_none_values({
        "id": state_data.get("id"),
        "name": state_data.get("name"),
        "type": state_data.get("type"),
        "color": state_data.get("color"),
        "position": state_data.get("position"),
    })


def clean_project_data(project_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format project data"""
    if not project_data:
        return {}

    return remove_none_values({
        "id": project_data.get("id"),
        "name": project_data.get("name"),
        "description": project_data.get("description"),
        "state": project_data.get("state"),
        "progress": project_data.get("progress"),
        "start_date": project_data.get("startDate"),
        "target_date": project_data.get("targetDate"),
        "url": project_data.get("url"),
    })


def clean_label_data(label_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format label data"""
    if not label_data:
        return {}

    return remove_none_values({
        "id": label_data.get("id"),
        "name": label_data.get("name"),
        "color": label_data.get("color"),
        "description": label_data.get("description"),
    })


def clean_cycle_data(cycle_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format cycle data"""
    if not cycle_data:
        return {}

    cleaned = {
        "id": cycle_data.get("id"),
        "number": cycle_data.get("number"),
        "name": cycle_data.get("name"),
        "description": cycle_data.get("description"),
        "starts_at": cycle_data.get("startsAt"),
        "ends_at": cycle_data.get("endsAt"),
        "completed_at": cycle_data.get("completedAt"),
        "auto_archived_at": cycle_data.get("autoArchivedAt"),
        "progress": cycle_data.get("progress"),
        "created_at": cycle_data.get("createdAt"),
        "updated_at": cycle_data.get("updatedAt"),
    }

    if cycle_data.get("team"):
        cleaned["team"] = clean_team_data(cycle_data["team"])

    if cycle_data.get("issues") and cycle_data["issues"].get("nodes"):
        cleaned["issues"] = [
            clean_issue_data(issue) for issue in cycle_data["issues"]["nodes"]
        ]

    return remove_none_values(cleaned)


def clean_relation_data(relation_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format issue relation data"""
    if not relation_data:
        return {}

    cleaned = {
        "id": relation_data.get("id"),
        "type": relation_data.get("type"),
    }

    # Clean related issue data
    if relation_data.get("relatedIssue"):
        cleaned["related_issue"] = {
            "id": relation_data["relatedIssue"].get("id"),
            "identifier": relation_data["relatedIssue"].get("identifier"),
            "title": relation_data["relatedIssue"].get("title"),
        }

    return remove_none_values(cleaned)


def clean_comment_data(comment_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format comment data"""
    if not comment_data:
        return {}

    cleaned = {
        "id": comment_data.get("id"),
        "body": comment_data.get("body"),
        "created_at": comment_data.get("createdAt"),
        "updated_at": comment_data.get("updatedAt"),
    }

    # Clean user data for comment author
    if comment_data.get("user"):
        cleaned["user"] = clean_user_data(comment_data["user"])

    return remove_none_values(cleaned)


def clean_attachment_data(attachment_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format attachment data"""
    if not attachment_data:
        return {}

    return remove_none_values({
        "id": attachment_data.get("id"),
        "title": attachment_data.get("title"),
        "subtitle": attachment_data.get("subtitle"),
        "url": attachment_data.get("url"),
        "metadata": attachment_data.get("metadata"),
        "created_at": attachment_data.get("createdAt"),
    })


def clean_template_data(template_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format template data"""
    if not template_data:
        return {}

    cleaned = {
        "id": template_data.get("id"),
        "name": template_data.get("name"),
        "description": template_data.get("description"),
        "created_at": template_data.get("createdAt"),
        "updated_at": template_data.get("updatedAt"),
        "template_data": template_data.get("templateData"),
    }

    # Clean creator data
    if template_data.get("creator"):
        cleaned["creator"] = clean_user_data(template_data["creator"])

    # Clean team data
    if template_data.get("team"):
        cleaned["team"] = clean_team_data(template_data["team"])

    return remove_none_values(cleaned)


def clean_workflow_state_data(state_data: dict[str, Any]) -> dict[str, Any]:
    """Clean and format workflow state data"""
    if not state_data:
        return {}

    cleaned = {
        "id": state_data.get("id"),
        "name": state_data.get("name"),
        "description": state_data.get("description"),
        "type": state_data.get("type"),
        "color": state_data.get("color"),
        "position": state_data.get("position"),
    }

    if state_data.get("team"):
        cleaned["team"] = clean_team_data(state_data["team"])

    return remove_none_values(cleaned)


def add_pagination_info(
    response: dict[str, Any], page_info: dict[str, Any]
) -> dict[str, Any]:
    """Add pagination information to response"""
    response["pagination"] = {
        "has_next_page": page_info.get("hasNextPage", False),
        "has_previous_page": page_info.get("hasPreviousPage", False),
        "start_cursor": page_info.get("startCursor"),
        "end_cursor": page_info.get("endCursor"),
    }
    return response


async def resolve_template_by_name(
    context: ToolContext, template_name: str, team_id: str | None = None
) -> dict[str, Any] | None:
    """Resolve a template name to template data

    This function finds Linear issue templates by name, which can be used for
    creating issues with predefined properties and even sub-issues.

    Args:
        context: Tool context with authentication
        template_name: Name of the template to find
        team_id: Optional team ID to scope template lookup. If not provided, searches all teams.

    Returns:
        Template data dictionary if found, None otherwise
    """
    if not template_name:
        return None

    client = LinearClient(context.get_auth_token_or_empty())

    if team_id:
        # Search templates for specific team
        templates_response = await client.get_templates(team_id=team_id)
        templates = templates_response.get("nodes", [])
    else:
        # Search templates across all teams
        templates_response = await client.get_templates()
        templates = templates_response.get("nodes", [])

    if not templates:
        return None

    # First try exact match (case insensitive)
    exact_matches = [
        template
        for template in templates
        if template.get("name", "").lower() == template_name.lower()
    ]

    if len(exact_matches) == 1:
        return clean_template_data(exact_matches[0])
    elif len(exact_matches) > 1:
        template_names = [
            f"{template['name']} ({template.get('team', {}).get('name', 'Global')})"
            for template in exact_matches
        ]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple templates found with name '{template_name}': {', '.join(template_names)}. "
            f"Please specify the template more precisely or provide a team context."
        )

    # Try partial match
    partial_matches = [
        template
        for template in templates
        if template_name.lower() in template.get("name", "").lower()
    ]

    if len(partial_matches) == 1:
        return clean_template_data(partial_matches[0])
    elif len(partial_matches) > 1:
        template_names = [
            f"{template['name']} ({template.get('team', {}).get('name', 'Global')})"
            for template in partial_matches
        ]
        raise ToolExecutionError(  # noqa: TRY003
            f"Multiple templates found containing '{template_name}': {', '.join(template_names)}. "
            f"Please specify the template more precisely or provide a team context."
        )

    return None
