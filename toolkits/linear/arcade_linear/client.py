import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

import httpx
from arcade_tdk.errors import ToolExecutionError

from arcade_linear.constants import (
    LINEAR_API_URL,
    LINEAR_MAX_CONCURRENT_REQUESTS,
    LINEAR_MAX_TIMEOUT_SECONDS,
)


@dataclass
class LinearClient:
    """Client for interacting with Linear's GraphQL API"""

    auth_token: str
    api_url: str = LINEAR_API_URL
    max_concurrent_requests: int = LINEAR_MAX_CONCURRENT_REQUESTS
    timeout_seconds: int = LINEAR_MAX_TIMEOUT_SECONDS
    _semaphore: asyncio.Semaphore | None = None

    def __post_init__(self) -> None:
        self._semaphore = self._semaphore or asyncio.Semaphore(self.max_concurrent_requests)

    def _build_headers(self, additional_headers: dict[str, str] | None = None) -> dict[str, str]:
        """Build headers for GraphQL requests"""
        headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if additional_headers:
            headers.update(additional_headers)
        return headers

    def _build_error_message(self, response: httpx.Response) -> tuple[str, str]:
        """Build user-friendly and developer error messages from response"""
        try:
            data = response.json()

            if data.get("errors"):
                errors = data["errors"]
                if len(errors) == 1:
                    error = errors[0]
                    user_message = error.get("message", "Unknown GraphQL error")
                    dev_message = f"{user_message} | Extensions: {error.get('extensions', {})} (HTTP {response.status_code})"
                else:
                    error_messages = [err.get("message", "Unknown error") for err in errors]
                    user_message = f"Multiple errors: {'; '.join(error_messages)}"
                    dev_message = f"Multiple GraphQL errors: {json.dumps(errors)} (HTTP {response.status_code})"
            else:
                user_message = f"HTTP {response.status_code}: {response.reason_phrase}"
                dev_message = f"HTTP {response.status_code}: {response.text}"

        except Exception as e:
            user_message = "Failed to parse Linear API error response"
            dev_message = f"Failed to parse error response: {type(e).__name__}: {e!s} | Raw response: {response.text}"

        return user_message, dev_message

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Raise appropriate errors for non-200 responses"""
        if response.status_code < 300:
            # Check for GraphQL errors in successful HTTP responses
            try:
                data = response.json()
                if data.get("errors"):
                    user_message, dev_message = self._build_error_message(response)
                    raise ToolExecutionError(user_message, developer_message=dev_message)
            except (ValueError, KeyError):
                # Response isn't JSON or doesn't have expected structure
                pass
            return

        user_message, dev_message = self._build_error_message(response)
        raise ToolExecutionError(user_message, developer_message=dev_message)

    async def execute_query(
        self, query: str, variables: dict[str, Any] | None = None, operation_name: str | None = None
    ) -> dict[str, Any]:
        """Execute a GraphQL query"""
        payload = {
            "query": query.strip(),
        }

        if variables:
            payload["variables"] = variables

        if operation_name:
            payload["operationName"] = operation_name

        headers = self._build_headers()

        async with self._semaphore, httpx.AsyncClient(timeout=self.timeout_seconds) as client:  # type: ignore[union-attr]
            response = await client.post(
                self.api_url,
                json=payload,
                headers=headers,
            )
            self._raise_for_status(response)
            return cast(dict[str, Any], response.json())

    async def execute_mutation(
        self,
        mutation: str,
        variables: dict[str, Any] | None = None,
        operation_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL mutation"""
        return await self.execute_query(mutation, variables, operation_name)

    async def get_viewer(self) -> dict[str, Any]:
        """Get current authenticated user information"""
        query = """
        query Viewer {
            viewer {
                id
                name
                email
                displayName
                avatarUrl
                organization {
                    id
                    name
                    urlKey
                }
            }
        }
        """

        result = await self.execute_query(query)
        return result["data"]["viewer"]

    async def get_teams(
        self,
        first: int = 50,
        after: str | None = None,
        include_archived: bool = False,
        name_filter: str | None = None,
    ) -> dict[str, Any]:
        """Get teams with optional filtering"""
        query = """
        query GetTeams($first: Int!, $after: String, $filter: TeamFilter) {
            teams(first: $first, after: $after, filter: $filter) {
                nodes {
                    id
                    key
                    name
                    description
                    private
                    archivedAt
                    createdAt
                    updatedAt
                    icon
                    color
                    cyclesEnabled
                    issueEstimationType
                    organization {
                        id
                        name
                    }
                    members {
                        nodes {
                            id
                            name
                            email
                            displayName
                            avatarUrl
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """

        # Build filter - removed isArchived as it doesn't exist in TeamFilter
        team_filter = {}
        # Note: Linear's TeamFilter doesn't have isArchived field based on API error
        # if not include_archived:
        #     team_filter["isArchived"] = {"eq": False}
        if name_filter:
            team_filter["name"] = {"containsIgnoreCase": name_filter}

        variables = {"first": first, "after": after, "filter": team_filter if team_filter else None}

        result = await self.execute_query(query, variables)
        return result["data"]["teams"]

    async def get_issues(
        self,
        first: int = 50,
        after: str | None = None,
        filter_conditions: dict[str, Any] | None = None,
        order_by: str | None = None,
    ) -> dict[str, Any]:
        """Get issues with filtering and sorting"""
        query = """
        query GetIssues($first: Int!, $after: String, $filter: IssueFilter, $orderBy: PaginationOrderBy) {
            issues(first: $first, after: $after, filter: $filter, orderBy: $orderBy) {
                nodes {
                    id
                    identifier
                    title
                    description
                    priority
                    priorityLabel
                    estimate
                    sortOrder
                    createdAt
                    updatedAt
                    completedAt
                    canceledAt
                    dueDate
                    url
                    branchName

                    creator {
                        id
                        name
                        email
                        displayName
                        avatarUrl
                    }

                    assignee {
                        id
                        name
                        email
                        displayName
                        avatarUrl
                    }

                    state {
                        id
                        name
                        type
                        color
                        position
                    }

                    team {
                        id
                        key
                        name
                    }

                    project {
                        id
                        name
                        description
                        state
                        progress
                        startDate
                        targetDate
                    }

                    cycle {
                        id
                        number
                        name
                        description
                        startsAt
                        endsAt
                        completedAt
                        progress
                    }

                    parent {
                        id
                        identifier
                        title
                    }

                    labels {
                        nodes {
                            id
                            name
                            color
                            description
                        }
                    }

                    children {
                        nodes {
                            id
                            identifier
                            title
                            state {
                                id
                                name
                                type
                            }
                        }
                    }

                    relations {
                        nodes {
                            id
                            type
                            relatedIssue {
                                id
                                identifier
                                title
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """

        variables = {
            "first": first,
            "after": after,
            "filter": filter_conditions,
            "orderBy": order_by,
        }

        result = await self.execute_query(query, variables)
        return result["data"]["issues"]

    async def get_issue_by_id(self, issue_id: str) -> dict[str, Any]:
        """Get a single issue by ID"""
        query = """
        query GetIssue($id: String!) {
            issue(id: $id) {
                id
                identifier
                title
                description
                priority
                priorityLabel
                estimate
                sortOrder
                createdAt
                updatedAt
                completedAt
                canceledAt
                dueDate
                url
                branchName

                creator {
                    id
                    name
                    email
                    displayName
                    avatarUrl
                }

                assignee {
                    id
                    name
                    email
                    displayName
                    avatarUrl
                }

                state {
                    id
                    name
                    type
                    color
                    position
                }

                team {
                    id
                    key
                    name
                }

                project {
                    id
                    name
                    description
                    state
                    progress
                    startDate
                    targetDate
                }

                cycle {
                    id
                    number
                    name
                    description
                    startsAt
                    endsAt
                    completedAt
                    progress
                }

                parent {
                    id
                    identifier
                    title
                }

                labels {
                    nodes {
                        id
                        name
                        color
                        description
                    }
                }

                attachments {
                    nodes {
                        id
                        title
                        subtitle
                        url
                        metadata
                        createdAt
                    }
                }

                comments {
                    nodes {
                        id
                        body
                        createdAt
                        updatedAt
                        user {
                            id
                            name
                            email
                            displayName
                        }
                    }
                }

                children {
                    nodes {
                        id
                        identifier
                        title
                        state {
                            id
                            name
                            type
                        }
                    }
                }

                relations {
                    nodes {
                        id
                        type
                        relatedIssue {
                            id
                            identifier
                            title
                        }
                    }
                }
            }
        }
        """

        variables = {"id": issue_id}
        result = await self.execute_query(query, variables)
        return result["data"]["issue"]

    async def create_issue(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new issue, optionally from a template"""
        mutation = """
        mutation CreateIssue($input: IssueCreateInput!) {
            issueCreate(input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    description
                    priority
                    priorityLabel
                    estimate
                    createdAt
                    url

                    creator {
                        id
                        name
                        email
                        displayName
                    }

                    assignee {
                        id
                        name
                        email
                        displayName
                    }

                    state {
                        id
                        name
                        type
                    }

                    team {
                        id
                        key
                        name
                    }

                    project {
                        id
                        name
                    }

                    cycle {
                        id
                        number
                        name
                    }

                    parent {
                        id
                        identifier
                        title
                    }

                    labels {
                        nodes {
                            id
                            name
                            color
                        }
                    }

                    children {
                        nodes {
                            id
                            identifier
                            title
                            state {
                                id
                                name
                                type
                            }
                        }
                    }
                }
            }
        }
        """

        variables = {"input": input_data}
        result = await self.execute_mutation(mutation, variables)
        return result["data"]["issueCreate"]

    async def update_issue(self, issue_id: str, input_data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing issue"""
        mutation = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
            issueUpdate(id: $id, input: $input) {
                success
                issue {
                    id
                    identifier
                    title
                    description
                    priority
                    priorityLabel
                    updatedAt
                    url

                    assignee {
                        id
                        name
                        email
                        displayName
                    }

                    state {
                        id
                        name
                        type
                    }

                    team {
                        id
                        key
                        name
                    }

                    project {
                        id
                        name
                    }

                    labels {
                        nodes {
                            id
                            name
                            color
                        }
                    }
                }
            }
        }
        """

        variables = {"id": issue_id, "input": input_data}
        result = await self.execute_mutation(mutation, variables)
        return result["data"]["issueUpdate"]

    # User-related methods
    async def get_users(
        self,
        first: int = 50,
        after: str | None = None,
        team_id: str | None = None,
        include_guests: bool = False,
    ) -> dict[str, Any]:
        """Get workspace users"""
        query = """
        query GetUsers($first: Int!, $after: String, $filter: UserFilter) {
            users(first: $first, after: $after, filter: $filter) {
                nodes {
                    id
                    name
                    email
                    displayName
                    avatarUrl
                    active
                    admin
                    guest
                    createdAt
                    updatedAt
                    timezone
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """

        # Build filter
        user_filter = {}
        if not include_guests:
            user_filter["isGuest"] = {"eq": False}
        if team_id:
            user_filter["assignedIssues"] = {"some": {"team": {"id": {"eq": team_id}}}}

        variables = {"first": first, "after": after, "filter": user_filter if user_filter else None}

        result = await self.execute_query(query, variables)
        return result["data"]["users"]

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        """Get user by email address"""
        query = """
        query GetUserByEmail($filter: UserFilter) {
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

        variables = {"filter": {"email": {"eq": email}}}
        result = await self.execute_query(query, variables)
        users = result["data"]["users"]["nodes"]
        return users[0] if users else None

    async def get_user_assigned_issues(
        self,
        user_id: str,
        first: int = 50,
        after: str | None = None,
        team_id: str | None = None,
        state_id: str | None = None,
        priority: int | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> dict[str, Any]:
        """Get issues assigned to a specific user"""
        # Build filter
        issue_filter = {"assignee": {"id": {"eq": user_id}}}

        if team_id:
            issue_filter["team"] = {"id": {"eq": team_id}}
        if state_id:
            issue_filter["state"] = {"id": {"eq": state_id}}
        if priority is not None:
            issue_filter["priority"] = {"eq": priority}

        # Build order - Linear API expects just the field name as a string
        order_by = None
        if sort_by:
            order_by = sort_by

        return await self.get_issues(
            first=first, after=after, filter_conditions=issue_filter, order_by=order_by
        )

    # Cycle-related methods
    async def get_cycles(
        self,
        first: int = 50,
        after: str | None = None,
        team_id: str | None = None,
        active_only: bool = True,
        include_completed: bool = False,
    ) -> dict[str, Any]:
        """Get cycles (sprints)"""
        query = """
        query GetCycles($first: Int!, $after: String, $filter: CycleFilter) {
            cycles(first: $first, after: $after, filter: $filter) {
                nodes {
                    id
                    number
                    name
                    description
                    startsAt
                    endsAt
                    completedAt
                    autoArchivedAt
                    progress
                    createdAt
                    updatedAt

                    team {
                        id
                        key
                        name
                    }

                    issues {
                        nodes {
                            id
                            identifier
                            title
                            state {
                                id
                                name
                                type
                            }
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """

        # Build filter
        cycle_filter = {}
        if team_id:
            cycle_filter["team"] = {"id": {"eq": team_id}}
        # Note: We cannot filter by completedAt null in CycleFilter as DateComparator doesn't support null checks
        # Instead, we'll filter the results after getting them from the API

        variables = {
            "first": first,
            "after": after,
            "filter": cycle_filter if cycle_filter else None,
        }

        result = await self.execute_query(query, variables)
        cycles_data = result["data"]["cycles"]

        # Filter out completed cycles if active_only is True (client-side filtering)
        if active_only and not include_completed:
            filtered_nodes = [
                cycle for cycle in cycles_data.get("nodes", []) if cycle.get("completedAt") is None
            ]
            cycles_data["nodes"] = filtered_nodes

        return cycles_data

    async def get_cycle_by_id(self, cycle_id: str) -> dict[str, Any] | None:
        """Get cycle by ID"""
        query = """
        query GetCycle($id: String!) {
            cycle(id: $id) {
                id
                number
                name
                description
                startsAt
                endsAt
                completedAt
                progress
                team {
                    id
                    key
                    name
                }
            }
        }
        """

        variables = {"id": cycle_id}
        result = await self.execute_query(query, variables)
        return result["data"]["cycle"]

    async def get_current_cycle(self, team_id: str) -> dict[str, Any] | None:
        """Get current active cycle for a team"""
        query = """
        query GetCurrentCycle($filter: CycleFilter) {
            cycles(filter: $filter, first: 1) {
                nodes {
                    id
                    number
                    name
                    description
                    startsAt
                    endsAt
                    progress
                    team {
                        id
                        key
                        name
                    }
                }
            }
        }
        """

        # Get current datetime in ISO format
        current_time = datetime.utcnow().isoformat() + "Z"

        # Filter for active cycles for the team
        cycle_filter = {
            "team": {"id": {"eq": team_id}},
            "startsAt": {"lte": current_time},
            "endsAt": {"gte": current_time},
        }

        variables = {"filter": cycle_filter}
        result = await self.execute_query(query, variables)
        cycles = result["data"]["cycles"]["nodes"]
        return cycles[0] if cycles else None

    async def get_cycle_issues(self, cycle_id: str) -> dict[str, Any]:
        """Get issues in a specific cycle"""
        issue_filter = {"cycle": {"id": {"eq": cycle_id}}}
        return await self.get_issues(filter_conditions=issue_filter)

    # Workflow state methods
    async def get_workflow_states(self, team_id: str | None = None) -> dict[str, Any]:
        """Get workflow states"""
        query = """
        query GetWorkflowStates($filter: WorkflowStateFilter) {
            workflowStates(filter: $filter) {
                nodes {
                    id
                    name
                    description
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
        state_filter = {}
        if team_id:
            state_filter["team"] = {"id": {"eq": team_id}}

        variables = {"filter": state_filter if state_filter else None}
        result = await self.execute_query(query, variables)
        return result["data"]["workflowStates"]

    async def create_workflow_state(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new workflow state"""
        mutation = """
        mutation CreateWorkflowState($input: WorkflowStateCreateInput!) {
            workflowStateCreate(input: $input) {
                success
                workflowState {
                    id
                    name
                    description
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

        variables = {"input": input_data}
        result = await self.execute_mutation(mutation, variables)
        return result["data"]["workflowStateCreate"]

    async def get_issues_by_state(
        self,
        state_id: str,
        first: int = 50,
        after: str | None = None,
        team_id: str | None = None,
        assignee_id: str | None = None,
        priority: int | None = None,
        sort_by: str | None = None,
        sort_direction: str | None = None,
    ) -> dict[str, Any]:
        """Get issues in a specific workflow state"""
        # Build filter
        issue_filter = {"state": {"id": {"eq": state_id}}}

        if team_id:
            issue_filter["team"] = {"id": {"eq": team_id}}
        if assignee_id:
            issue_filter["assignee"] = {"id": {"eq": assignee_id}}
        if priority is not None:
            issue_filter["priority"] = {"eq": priority}

        # Build order - Linear API expects just the field name as a string
        order_by = None
        if sort_by:
            order_by = sort_by

        return await self.get_issues(
            first=first, after=after, filter_conditions=issue_filter, order_by=order_by
        )

    async def get_completed_issues(
        self,
        first: int = 50,
        after: str | None = None,
        team_id: str | None = None,
        assignee_id: str | None = None,
        completed_after: str | None = None,
        completed_before: str | None = None,
    ) -> dict[str, Any]:
        """Get completed issues"""
        # Build filter for completed states
        issue_filter = {"state": {"type": {"eq": "completed"}}}

        if team_id:
            issue_filter["team"] = {"id": {"eq": team_id}}
        if assignee_id:
            issue_filter["assignee"] = {"id": {"eq": assignee_id}}
        if completed_after:
            issue_filter.setdefault("completedAt", {})["gte"] = completed_after
        if completed_before:
            issue_filter.setdefault("completedAt", {})["lte"] = completed_before

        return await self.get_issues(first=first, after=after, filter_conditions=issue_filter)

    # Project-related methods
    async def get_projects(
        self,
        first: int = 50,
        after: str | None = None,
        team_id: str | None = None,
        status: str | None = None,
        include_archived: bool = False,
        created_after: str | None = None,
    ) -> dict[str, Any]:
        """Get projects"""
        query = """
        query GetProjects($first: Int!, $after: String, $filter: ProjectFilter) {
            projects(first: $first, after: $after, filter: $filter) {
                nodes {
                    id
                    name
                    description
                    state
                    progress
                    startDate
                    targetDate
                    completedAt
                    canceledAt
                    autoArchivedAt
                    createdAt
                    updatedAt
                    icon
                    color

                    creator {
                        id
                        name
                        email
                        displayName
                    }

                    lead {
                        id
                        name
                        email
                        displayName
                    }

                    teams {
                        nodes {
                            id
                            key
                            name
                        }
                    }

                    members {
                        nodes {
                            id
                            name
                            email
                            displayName
                        }
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """

        # Build filter
        project_filter = {}
        if team_id:
            project_filter["teams"] = {"some": {"id": {"eq": team_id}}}
        if status:
            project_filter["state"] = {"eq": status}
        if not include_archived:
            # Linear API doesn't have archivedAt in ProjectFilter, use canceledAt instead
            project_filter["canceledAt"] = {"null": True}
        if created_after:
            project_filter["createdAt"] = {"gte": created_after}

        variables = {
            "first": first,
            "after": after,
            "filter": project_filter if project_filter else None,
        }

        result = await self.execute_query(query, variables)
        return result["data"]["projects"]

    async def get_project_by_id(self, project_id: str) -> dict[str, Any] | None:
        """Get project by ID"""
        query = """
        query GetProject($id: String!) {
            project(id: $id) {
                id
                name
                description
                state
                progress
                startDate
                targetDate
                teams {
                    nodes {
                        id
                        key
                        name
                    }
                }
            }
        }
        """

        variables = {"id": project_id}
        result = await self.execute_query(query, variables)
        return result["data"]["project"]

    async def get_project_issues(
        self,
        project_id: str,
        first: int = 50,
        after: str | None = None,
        team_id: str | None = None,
        state_id: str | None = None,
        assignee_id: str | None = None,
    ) -> dict[str, Any]:
        """Get issues in a specific project"""
        # Build filter
        issue_filter = {"project": {"id": {"eq": project_id}}}

        if team_id:
            issue_filter["team"] = {"id": {"eq": team_id}}
        if state_id:
            issue_filter["state"] = {"id": {"eq": state_id}}
        if assignee_id:
            issue_filter["assignee"] = {"id": {"eq": assignee_id}}

        return await self.get_issues(first=first, after=after, filter_conditions=issue_filter)

    # Label management methods
    async def get_labels(self, team_id: str | None = None, first: int = 100) -> dict[str, Any]:
        """Get all labels, optionally filtered by team"""
        query = """
        query GetLabels($first: Int!, $filter: IssueLabelFilter) {
            issueLabels(first: $first, filter: $filter) {
                nodes {
                    id
                    name
                    color
                    description
                    creator {
                        id
                        name
                    }
                    team {
                        id
                        key
                        name
                    }
                }
                pageInfo {
                    hasNextPage
                    hasPreviousPage
                    startCursor
                    endCursor
                }
            }
        }
        """

        # Build filter
        label_filter = {}
        if team_id:
            label_filter["team"] = {"id": {"eq": team_id}}

        variables = {"first": first, "filter": label_filter if label_filter else None}

        result = await self.execute_query(query, variables)
        return result["data"]["issueLabels"]

    async def create_label(
        self,
        name: str,
        team_id: str | None = None,
        color: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Create a new label"""
        mutation = """
        mutation CreateLabel($input: IssueLabelCreateInput!) {
            issueLabelCreate(input: $input) {
                success
                issueLabel {
                    id
                    name
                    color
                    description
                    team {
                        id
                        key
                        name
                    }
                }
            }
        }
        """

        # Build input
        label_input = {"name": name}

        if team_id:
            label_input["teamId"] = team_id
        if color:
            label_input["color"] = color
        if description:
            label_input["description"] = description

        variables = {"input": label_input}
        result = await self.execute_mutation(mutation, variables)
        response = result["data"]["issueLabelCreate"]
        # Fix the field name inconsistency
        if response.get("success") and response.get("issueLabel"):
            response["label"] = response["issueLabel"]
        return response

    # Template-related methods
    async def get_templates(self, team_id: str | None = None, first: int = 50) -> dict[str, Any]:
        """Get issue templates for a specific team"""
        if team_id:
            # Get templates for a specific team
            query = """
            query GetTeamTemplates($teamId: String!) {
                team(id: $teamId) {
                    id
                    name
                    templates {
                        nodes {
                            id
                            name
                            description
                            createdAt
                            updatedAt

                            creator {
                                id
                                name
                                email
                                displayName
                            }

                            team {
                                id
                                key
                                name
                            }

                            templateData
                        }
                    }
                }
            }
            """

            variables = {"teamId": team_id}
            result = await self.execute_query(query, variables)
            team_data = result["data"]["team"]
            if team_data and team_data.get("templates") and team_data["templates"].get("nodes"):
                return {"nodes": team_data["templates"]["nodes"]}
            else:
                return {"nodes": []}
        else:
            # Get all templates across all teams
            # First get all teams, then get templates for each team
            teams_response = await self.get_teams(first=100)
            all_templates = []

            for team in teams_response.get("nodes", []):
                team_templates_response = await self.get_templates(team_id=team["id"])
                all_templates.extend(team_templates_response.get("nodes", []))

            return {"nodes": all_templates}

    async def get_template_by_id(self, template_id: str) -> dict[str, Any] | None:
        """Get template by ID"""
        query = """
        query GetTemplate($id: String!) {
            template(id: $id) {
                id
                name
                description
                createdAt
                updatedAt

                creator {
                    id
                    name
                    email
                    displayName
                }

                team {
                    id
                    key
                    name
                }

                templateData
            }
        }
        """

        variables = {"id": template_id}
        result = await self.execute_query(query, variables)
        return result["data"]["template"]

    async def create_project(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new project"""
        mutation = """
        mutation CreateProject($input: ProjectCreateInput!) {
            projectCreate(input: $input) {
                success
                project {
                    id
                    name
                    description
                    state
                    progress
                    startDate
                    targetDate
                    createdAt
                    url

                    creator {
                        id
                        name
                        email
                        displayName
                    }

                    lead {
                        id
                        name
                        email
                        displayName
                    }

                    teams {
                        nodes {
                            id
                            key
                            name
                        }
                    }
                }
            }
        }
        """

        variables = {"input": input_data}
        result = await self.execute_query(mutation, variables)
        return result["data"]["projectCreate"]

    async def create_comment(self, issue_id: str, comment_body: str) -> dict[str, Any]:
        """Create a comment on an issue"""
        mutation = """
        mutation CreateComment($input: CommentCreateInput!) {
            commentCreate(input: $input) {
                success
                comment {
                    id
                    body
                    createdAt
                    updatedAt
                    user {
                        id
                        name
                        email
                        displayName
                    }
                    issue {
                        id
                        identifier
                        title
                    }
                }
            }
        }
        """

        variables = {"input": {"issueId": issue_id, "body": comment_body}}
        result = await self.execute_query(mutation, variables)
        return result["data"]["commentCreate"]
