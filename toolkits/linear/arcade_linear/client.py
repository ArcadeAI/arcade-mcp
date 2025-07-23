import asyncio
import json
from dataclasses import dataclass
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
                    dev_message = (
                        f"GraphQL error: {json.dumps(error)} (HTTP {response.status_code})"
                    )
                else:
                    error_messages = [err.get("message", "Unknown error") for err in errors]
                    user_message = f"Multiple errors: {'; '.join(error_messages)}"
                    dev_message = (
                        f"Multiple GraphQL errors: {json.dumps(errors)} "
                        f"(HTTP {response.status_code})"
                    )
            else:
                user_message = f"HTTP {response.status_code}: {response.reason_phrase}"
                dev_message = f"HTTP {response.status_code}: {response.text}"

        except Exception as e:
            user_message = "Failed to parse Linear API error response"
            dev_message = (
                f"Failed to parse error response: {type(e).__name__}: {e!s} | "
                f"Raw response: {response.text}"
            )

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
        payload: dict[str, Any] = {
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

        # Build filter
        team_filter = {}
        if name_filter:
            team_filter["name"] = {"containsIgnoreCase": name_filter}

        variables = {"first": first, "after": after, "filter": team_filter if team_filter else None}

        result = await self.execute_query(query, variables)
        return cast(dict[str, Any], result["data"]["teams"])

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
        return cast(dict[str, Any], result["data"]["issue"])
