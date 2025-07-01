from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from arcade_linear.constants import IssuePriority, ProjectState, WorkflowStateType


@dataclass
class LinearUser:
    """Represents a Linear user"""

    id: str
    name: str
    email: str
    display_name: str | None = None
    avatar_url: str | None = None
    active: bool = True
    admin: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    timezone: str | None = None


@dataclass
class LinearTeam:
    """Represents a Linear team"""

    id: str
    key: str
    name: str
    description: str | None = None
    private: bool = False
    archived_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    icon: str | None = None
    color: str | None = None
    cycles_enabled: bool = False
    members: list[LinearUser] = None
    organization_id: str | None = None

    def __post_init__(self):
        if self.members is None:
            self.members = []


@dataclass
class WorkflowState:
    """Represents a Linear workflow state"""

    id: str
    name: str
    type: WorkflowStateType
    color: str | None = None
    description: str | None = None
    position: float = 0.0
    team_id: str | None = None


@dataclass
class LinearLabel:
    """Represents a Linear label"""

    id: str
    name: str
    color: str | None = None
    description: str | None = None


@dataclass
class LinearProject:
    """Represents a Linear project"""

    id: str
    name: str
    description: str | None = None
    state: ProjectState = ProjectState.PLANNED
    progress: float = 0.0
    start_date: datetime | None = None
    target_date: datetime | None = None
    completed_at: datetime | None = None
    canceled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    url: str | None = None
    icon: str | None = None
    color: str | None = None
    creator: LinearUser | None = None
    lead: LinearUser | None = None
    teams: list[LinearTeam] = None
    members: list[LinearUser] = None

    def __post_init__(self):
        if self.teams is None:
            self.teams = []
        if self.members is None:
            self.members = []


@dataclass
class LinearCycle:
    """Represents a Linear cycle"""

    id: str
    number: int
    name: str | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    completed_at: datetime | None = None
    progress: float = 0.0
    url: str | None = None


@dataclass
class LinearAttachment:
    """Represents a Linear attachment"""

    id: str
    title: str
    subtitle: str | None = None
    url: str | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None


@dataclass
class LinearComment:
    """Represents a Linear comment"""

    id: str
    body: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    user: LinearUser | None = None


@dataclass
class IssueRelation:
    """Represents a relation between issues"""

    id: str
    type: str
    related_issue_id: str
    related_issue_identifier: str | None = None
    related_issue_title: str | None = None


@dataclass
class LinearIssue:
    """Represents a Linear issue"""

    id: str
    identifier: str
    title: str
    description: str | None = None
    priority: IssuePriority = IssuePriority.NO_PRIORITY
    priority_label: str = "No priority"
    estimate: float | None = None
    sort_order: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    canceled_at: datetime | None = None
    due_date: datetime | None = None
    url: str | None = None
    branch_name: str | None = None

    # Related entities
    creator: LinearUser | None = None
    assignee: LinearUser | None = None
    state: WorkflowState | None = None
    team: LinearTeam | None = None
    project: LinearProject | None = None
    cycle: LinearCycle | None = None
    parent: Optional["LinearIssue"] = None
    labels: list[LinearLabel] = None
    attachments: list[LinearAttachment] = None
    comments: list[LinearComment] = None
    relations: list[IssueRelation] = None
    children: list["LinearIssue"] = None

    def __post_init__(self):
        if self.labels is None:
            self.labels = []
        if self.attachments is None:
            self.attachments = []
        if self.comments is None:
            self.comments = []
        if self.relations is None:
            self.relations = []
        if self.children is None:
            self.children = []


@dataclass
class GraphQLFilter:
    """Represents a GraphQL filter condition"""

    field: str
    operator: str
    value: Any


@dataclass
class IssueFilter:
    """Filter conditions for issue searches"""

    team_id: str | None = None
    assignee_id: str | None = None
    creator_id: str | None = None
    state_id: str | None = None
    priority: IssuePriority | None = None
    label_ids: list[str] = None
    project_id: str | None = None
    cycle_id: str | None = None
    parent_id: str | None = None
    created_at_gte: datetime | None = None
    created_at_lte: datetime | None = None
    updated_at_gte: datetime | None = None
    updated_at_lte: datetime | None = None
    completed_at_gte: datetime | None = None
    completed_at_lte: datetime | None = None
    due_date_gte: datetime | None = None
    due_date_lte: datetime | None = None
    search_query: str | None = None

    def __post_init__(self):
        if self.label_ids is None:
            self.label_ids = []


@dataclass
class TeamFilter:
    """Filter conditions for team searches"""

    archived: bool | None = None
    created_at_gte: datetime | None = None
    created_at_lte: datetime | None = None
    name_contains: str | None = None


@dataclass
class LinearResponse:
    """Represents a response from Linear API"""

    data: dict[str, Any]
    errors: list[dict[str, Any]] = None
    extensions: dict[str, Any] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.extensions is None:
            self.extensions = {}


@dataclass
class PaginationInfo:
    """Represents pagination information"""

    has_next_page: bool = False
    has_previous_page: bool = False
    start_cursor: str | None = None
    end_cursor: str | None = None


@dataclass
class PageInfo:
    """Represents page info with count"""

    total_count: int = 0
    page_size: int = 50
    has_next_page: bool = False
    start_cursor: str | None = None
    end_cursor: str | None = None


class SortDirection(Enum):
    """Sort direction for queries"""

    ASC = "ASC"
    DESC = "DESC"


class IssueSortField(Enum):
    """Available fields for sorting issues"""

    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"
    PRIORITY = "priority"
    DUE_DATE = "dueDate"
    TITLE = "title"
    ESTIMATE = "estimate"


@dataclass
class IssueSort:
    """Sort configuration for issues"""

    field: IssueSortField = IssueSortField.UPDATED_AT
    direction: SortDirection = SortDirection.DESC


@dataclass
class CreateIssueInput:
    """Input data for creating an issue"""

    title: str
    team_id: str
    description: str | None = None
    assignee_id: str | None = None
    priority: IssuePriority | None = None
    state_id: str | None = None
    label_ids: list[str] = None
    project_id: str | None = None
    cycle_id: str | None = None
    parent_id: str | None = None
    due_date: datetime | None = None
    estimate: float | None = None

    def __post_init__(self):
        if self.label_ids is None:
            self.label_ids = []


@dataclass
class UpdateIssueInput:
    """Input data for updating an issue"""

    title: str | None = None
    description: str | None = None
    assignee_id: str | None = None
    priority: IssuePriority | None = None
    state_id: str | None = None
    label_ids: list[str] = None
    project_id: str | None = None
    cycle_id: str | None = None
    parent_id: str | None = None
    due_date: datetime | None = None
    estimate: float | None = None

    def __post_init__(self):
        if self.label_ids is None:
            self.label_ids = []
