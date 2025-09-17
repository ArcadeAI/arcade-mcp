#!/usr/bin/env python3
"""
Enums for Pylon-GitHub sync integration.
"""

from enum import Enum


class PylonIssueType(Enum):
    """Pylon issue types."""

    CONVERSATION = "Conversation"
    BUG = "Bug"
    QUESTION = "Question"
    FEATURE_REQUEST = "Feature Request"
    INCIDENT = "Incident"
    TASK = "Task"
    COMPLAINT = "Complaint"
    FEEDBACK = "Feedback"


class PylonIssueState(Enum):
    """Pylon issue states."""

    NEW = "new"
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    RESOLVED = "resolved"


class GitHubAction(Enum):
    """GitHub event actions."""

    # Issue actions
    OPENED = "opened"
    EDITED = "edited"
    REOPENED = "reopened"
    CLOSED = "closed"

    # Discussion actions
    CREATED = "created"
    ANSWERED = "answered"
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class ExternalSource(Enum):
    """External source types for linking issues."""

    GITHUB = "github"
    SLACK = "slack"
    EMAIL = "email"
    WEB = "web"
    API = "api"
