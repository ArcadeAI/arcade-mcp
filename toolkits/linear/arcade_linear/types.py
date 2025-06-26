from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from arcade_linear.constants import IssuePriority, WorkflowStateType, ProjectState


@dataclass
class LinearUser:
    """Represents a Linear user"""
    id: str
    name: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    active: bool = True
    admin: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    timezone: Optional[str] = None


@dataclass
class LinearTeam:
    """Represents a Linear team"""
    id: str
    key: str
    name: str
    description: Optional[str] = None
    private: bool = False
    archived_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    cycles_enabled: bool = False
    members: List[LinearUser] = None
    organization_id: Optional[str] = None

    def __post_init__(self):
        if self.members is None:
            self.members = []


@dataclass
class WorkflowState:
    """Represents a Linear workflow state"""
    id: str
    name: str
    type: WorkflowStateType
    color: Optional[str] = None
    description: Optional[str] = None
    position: float = 0.0
    team_id: Optional[str] = None


@dataclass
class LinearLabel:
    """Represents a Linear label"""
    id: str
    name: str
    color: Optional[str] = None
    description: Optional[str] = None


@dataclass
class LinearProject:
    """Represents a Linear project"""
    id: str
    name: str
    description: Optional[str] = None
    state: ProjectState = ProjectState.PLANNED
    progress: float = 0.0
    start_date: Optional[datetime] = None
    target_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    url: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    creator: Optional[LinearUser] = None
    lead: Optional[LinearUser] = None
    teams: List[LinearTeam] = None
    members: List[LinearUser] = None

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
    name: Optional[str] = None
    description: Optional[str] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    url: Optional[str] = None


@dataclass
class LinearAttachment:
    """Represents a Linear attachment"""
    id: str
    title: str
    subtitle: Optional[str] = None
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None


@dataclass
class LinearComment:
    """Represents a Linear comment"""
    id: str
    body: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    user: Optional[LinearUser] = None


@dataclass
class IssueRelation:
    """Represents a relation between issues"""
    id: str
    type: str
    related_issue_id: str
    related_issue_identifier: Optional[str] = None
    related_issue_title: Optional[str] = None


@dataclass
class LinearIssue:
    """Represents a Linear issue"""
    id: str
    identifier: str
    title: str
    description: Optional[str] = None
    priority: IssuePriority = IssuePriority.NO_PRIORITY
    priority_label: str = "No priority"
    estimate: Optional[float] = None
    sort_order: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    canceled_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    url: Optional[str] = None
    branch_name: Optional[str] = None
    
    # Related entities
    creator: Optional[LinearUser] = None
    assignee: Optional[LinearUser] = None
    state: Optional[WorkflowState] = None
    team: Optional[LinearTeam] = None
    project: Optional[LinearProject] = None
    cycle: Optional[LinearCycle] = None
    parent: Optional['LinearIssue'] = None
    labels: List[LinearLabel] = None
    attachments: List[LinearAttachment] = None
    comments: List[LinearComment] = None
    relations: List[IssueRelation] = None
    children: List['LinearIssue'] = None

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
    team_id: Optional[str] = None
    assignee_id: Optional[str] = None
    creator_id: Optional[str] = None
    state_id: Optional[str] = None
    priority: Optional[IssuePriority] = None
    label_ids: List[str] = None
    project_id: Optional[str] = None
    cycle_id: Optional[str] = None
    parent_id: Optional[str] = None
    created_at_gte: Optional[datetime] = None
    created_at_lte: Optional[datetime] = None
    updated_at_gte: Optional[datetime] = None
    updated_at_lte: Optional[datetime] = None
    completed_at_gte: Optional[datetime] = None
    completed_at_lte: Optional[datetime] = None
    due_date_gte: Optional[datetime] = None
    due_date_lte: Optional[datetime] = None
    search_query: Optional[str] = None

    def __post_init__(self):
        if self.label_ids is None:
            self.label_ids = []


@dataclass
class TeamFilter:
    """Filter conditions for team searches"""
    archived: Optional[bool] = None
    created_at_gte: Optional[datetime] = None
    created_at_lte: Optional[datetime] = None
    name_contains: Optional[str] = None


@dataclass
class LinearResponse:
    """Represents a response from Linear API"""
    data: Dict[str, Any]
    errors: List[Dict[str, Any]] = None
    extensions: Dict[str, Any] = None

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
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None


@dataclass
class PageInfo:
    """Represents page info with count"""
    total_count: int = 0
    page_size: int = 50
    has_next_page: bool = False
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None


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
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[IssuePriority] = None
    state_id: Optional[str] = None
    label_ids: List[str] = None
    project_id: Optional[str] = None
    cycle_id: Optional[str] = None
    parent_id: Optional[str] = None
    due_date: Optional[datetime] = None
    estimate: Optional[float] = None

    def __post_init__(self):
        if self.label_ids is None:
            self.label_ids = []


@dataclass
class UpdateIssueInput:
    """Input data for updating an issue"""
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: Optional[IssuePriority] = None
    state_id: Optional[str] = None
    label_ids: List[str] = None
    project_id: Optional[str] = None
    cycle_id: Optional[str] = None
    parent_id: Optional[str] = None
    due_date: Optional[datetime] = None
    estimate: Optional[float] = None

    def __post_init__(self):
        if self.label_ids is None:
            self.label_ids = [] 