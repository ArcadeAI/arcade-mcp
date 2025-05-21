import os
from enum import Enum

JIRA_BASE_URL = "https://api.atlassian.com/ex/jira"
JIRA_API_VERSION = "3"

try:
    JIRA_MAX_CONCURRENT_REQUESTS = int(os.getenv("JIRA_MAX_CONCURRENT_REQUESTS", 3))
except Exception:
    JIRA_MAX_CONCURRENT_REQUESTS = 3

JIRA_ISSUE_FIELDS = [
    "id",
    "key",
    "summary",
    "description",
    "labels",
    "project",
    "comment",
    "issuelinks",
    "assignee",
    "creator",
    "duedate",
    "issuetype",
    "priority",
    "progress",
    "project",
    "reporter",
    "status",
    "subtasks",
    "resolution",
    "resolutiondate",
]


class IssueStatus(Enum):
    TO_DO = "To Do"
    IN_PROGRESS = "In Progress"
    DONE = "Done"


class IssuePriority(Enum):
    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class IssueType(Enum):
    TASK = "Task"
    BUG = "Bug"
    STORY = "Story"
    EPIC = "Epic"
