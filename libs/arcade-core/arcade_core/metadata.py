from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict


class Verb(str, Enum):
    """
    Classifies the primary action performed by the tool.

    Design: Based on CRUD + common automation actions.
    Single value per tool.
    """

    CREATE = "create"  # Generates new resources
    READ = "read"  # Retrieves existing data
    UPDATE = "update"  # Modifies existing resources
    DELETE = "delete"  # Removes resources
    EXECUTE = "execute"  # Runs processes, triggers actions
    TRANSFER = "transfer"  # Moves/syncs data between systems
    LINK = "link"  # Associates or disassociates resources
    CONTROL = "control"  # Start/stop/pause lifecycle operations
    AUTHORIZE = "authorize"  # Grants or revokes permissions
    MONITOR = "monitor"  # Observes, tracks, or subscribes to changes


class Scope(str, Enum):
    """
    Defines where the tool operates.

    Single value per tool.
    """

    LOCAL = "local"  # Runs entirely in-process
    REMOTE = "remote"  # Interacts with external services/APIs
    HYBRID = "hybrid"  # Both local computation and remote calls


class Domain(str, Enum):
    """
    High-level functional domain the tool serves.

    Design: Based on existing SaaS marketplace category taxonomies.
    Tools can belong to multiple domains.

    Litmus test: Would this category appear in a SaaS marketplace filter?
    """

    COMMUNICATION = "communication"  # Messaging, email, notifications
    PRODUCTIVITY = "productivity"  # Docs, tasks, notes, collaboration
    SCHEDULING = "scheduling"  # Calendars, appointments, time
    STORAGE = "storage"  # Files, drives, databases
    CRM = "crm"  # Customer relationships, contacts
    SALES = "sales"  # Deals, pipelines, quoting
    MARKETING = "marketing"  # Campaigns, social, content
    SUPPORT = "support"  # Helpdesk, tickets, success
    FINANCE = "finance"  # Accounting, payments, invoicing
    HR = "hr"  # Recruiting, onboarding, people
    ENGINEERING = "engineering"  # Code, repos, DevOps, infra
    ANALYTICS = "analytics"  # Reporting, BI, metrics
    SECURITY = "security"  # Access control, compliance
    IDENTITY = "identity"  # User profiles, credentials, authentication
    ECOMMERCE = "ecommerce"  # Stores, inventory, fulfillment
    UTILITY = "utility"  # Pure computation, transformation, generation


class Annotations(BaseModel):
    """MCP-compatible tool annotations (behavioral hints). Uses camelCase to match MCP spec."""

    title: str | None = None  # Falls back to function name
    readOnlyHint: bool = False  # Only reads data, no mutations
    destructiveHint: bool = True  # MCP default: assume destructive
    idempotentHint: bool = False  # Repeated calls have no additional effect
    openWorldHint: bool = True  # Interacts with external systems

    model_config = ConfigDict(extra="allow")


class Categories(BaseModel):
    """
    Arcade-defined tool categorization. Static across all deployments.
    These properties are intrinsic to the tool's code, not user-configurable.

    A tool is fully described by:
    (one Verb) + (one Scope) + (one or more Domains)
    """

    verb: Verb | None = None  # Single: What action
    scope: Scope | None = None  # Single: System boundary
    domains: list[Domain] | None = None  # Multiple: Functional areas

    model_config = ConfigDict(extra="allow")


class ToolMetadata(BaseModel):
    """
    Container for tool metadata. Static properties defined by tool authors.

    Note: Tags are NOT defined here - they are customer-defined via GUI/API
    and stored separately. Only categories, annotations, and extensions can be defined in code.

    The `extensions` field allows tool authors to define arbitrary key/values
    for custom logic (e.g., IDP routing, feature flags). These are NOT used
    by tool selection scoring.
    """

    annotations: Annotations | None = None
    categories: Categories | None = None
    extensions: dict[str, Any] | None = None

    model_config = ConfigDict(extra="forbid")
