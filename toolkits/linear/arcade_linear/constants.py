import os
from enum import Enum

LINEAR_API_URL = "https://api.linear.app/graphql"

try:
    LINEAR_MAX_CONCURRENT_REQUESTS = int(os.getenv("LINEAR_MAX_CONCURRENT_REQUESTS", 3))
except ValueError:
    LINEAR_MAX_CONCURRENT_REQUESTS = 3

try:
    LINEAR_MAX_TIMEOUT_SECONDS = int(os.getenv("LINEAR_MAX_TIMEOUT_SECONDS", 30))
except ValueError:
    LINEAR_MAX_TIMEOUT_SECONDS = 30


# Sort options for issues - Linear API expects camelCase enum values
class IssueSortField(Enum):
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"
    PRIORITY = "priority"
    TITLE = "title"
    DUE_DATE = "dueDate"
    ESTIMATE = "estimate"


class SortDirection(Enum):
    ASC = "ASC"
    DESC = "DESC"


# GraphQL field selections for different entity types
TEAM_FIELDS = """
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
    issueOrderingNoPriorityFirst
    markedAsDuplicateWorkflowState {
        id
        name
    }
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
"""

ISSUE_FIELDS = """
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
    autoClosedAt
    autoArchivedAt
    dueDate
    triagedAt
    snoozedUntilAt
    url
    branchName
    customerTicketCount

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
        autoArchivedAt
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
"""

USER_FIELDS = """
    id
    name
    email
    displayName
    avatarUrl
    active
    admin
    createdAt
    updatedAt
    timezone
    inviteHash
"""

PROJECT_FIELDS = """
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
"""

WORKFLOW_STATE_FIELDS = """
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
"""

CYCLE_FIELDS = """
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
"""


# Priority mappings
class IssuePriority(Enum):
    NO_PRIORITY = 0
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


PRIORITY_LABELS = {0: "No priority", 1: "Urgent", 2: "High", 3: "Medium", 4: "Low"}

PRIORITY_NAME_TO_VALUE = {
    "no priority": 0,
    "none": 0,
    "urgent": 1,
    "high": 2,
    "medium": 3,
    "low": 4,
}


# Workflow state types
class WorkflowStateType(Enum):
    BACKLOG = "backlog"
    UNSTARTED = "unstarted"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"


# Issue relation types
class IssueRelationType(Enum):
    BLOCKS = "blocks"
    BLOCKED_BY = "blockedBy"
    DUPLICATE = "duplicate"
    DUPLICATED_BY = "duplicatedBy"
    RELATES = "relates"


# Project states
class ProjectState(Enum):
    PLANNED = "planned"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"
    PAUSED = "paused"


# Project status (alias for consistency with API)
class ProjectStatus(Enum):
    PLANNED = "planned"
    STARTED = "started"
    COMPLETED = "completed"
    CANCELED = "canceled"
    PAUSED = "paused"


# Common filter operators for search
class FilterOperator(Enum):
    EQ = "eq"
    NEQ = "neq"
    IN = "in"
    NIN = "nin"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    CONTAINS = "contains"
    NOT_CONTAINS = "notContains"
    STARTS_WITH = "startsWith"
    NOT_STARTS_WITH = "notStartsWith"
    ENDS_WITH = "endsWith"
    NOT_ENDS_WITH = "notEndsWith"


# Time range mappings for date parsing
TIME_RANGE_MAPPINGS = {
    "today": "today",
    "yesterday": "yesterday",
    "this week": "this week",
    "last week": "last week",
    "this month": "this month",
    "last month": "last month",
    "this year": "this year",
    "last year": "last year",
}

# Common GraphQL queries
VIEWER_QUERY = """
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
        }
    }
}
"""
