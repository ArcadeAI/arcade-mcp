"""
Tool Metadata

Defines the metadata model for Arcade tools. This module provides three layers:

- Classification: What the tool is FOR (domains) and what it connects to (system_types).
  Used for tool discovery and search boosting.

- Behavior: What effects the tool has. MCP Annotations are computed from this.
  Commonly used for policy decisions (HITL gates, retry logic, etc.)

- Extras: Arbitrary key/values for custom logic (IDP routing, feature flags, etc.)
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from arcade_core.errors import ToolDefinitionError


class Domain(str, Enum):
    """
    The capability areas this tool operates in.

    Used for Arcade tool selection boosting.
    Tools can specify multiple domains to accurately represent their capabilities.

    Choose the domain that answers: "What is this tool fundamentally FOR?"
    """

    # === Communication ===
    MESSAGING = "messaging"
    """Send or receive messages between parties. Examples: Gmail.SendEmail, Slack.SendMessage, Twilio.SendSMS"""

    # === Content ===
    DOCUMENTS = "documents"
    """Create, read, or edit text-based content. Examples: Google Docs, Notion.CreatePage, Confluence"""

    MEDIA = "media"
    """Create or process images, video, or audio. Examples: Figma exports, YouTube uploads, transcription"""

    CODE = "code"
    """Work with source code or software artifacts. Examples: GitHub.CreatePR, GitLab branches, code execution"""

    # === Data ===
    STORAGE = "storage"
    """Store, retrieve, or organize files. Examples: GoogleDrive.Upload, S3.PutObject, Dropbox"""

    SEARCH = "search"
    """Find or discover information. Examples: Web search, Firecrawl.ScrapeUrl, Algolia"""

    TRANSFORM = "transform"
    """Convert, compute, or reshape data. Examples: Math operations, JSON parsing, format conversion"""

    ANALYTICS = "analytics"
    """Measure, aggregate, or report on data. Examples: Mixpanel.GetMetrics, PostHog, dashboards"""

    # === Planning ===
    SCHEDULING = "scheduling"
    """Manage calendars, appointments, or bookings. Examples: GoogleCalendar.CreateEvent, Calendly"""

    TASKS = "tasks"
    """Track work items, issues, or tickets. Examples: Jira.CreateIssue, Asana, Linear, Zendesk tickets"""

    WORKFLOW = "workflow"
    """Orchestrate or automate multi-step processes. Examples: Zapier.TriggerZap, Temporal, Airflow"""

    # === Transactions ===
    COMMERCE = "commerce"
    """Manage orders, deals, or inventory. Examples: Shopify orders, Salesforce opportunities"""

    PAYMENTS = "payments"
    """Process payments or invoices. Examples: Stripe.CreatePayment, QuickBooks, PayPal"""

    # === Records ===
    RECORDS = "records"
    """Manage entity records (contacts, accounts, etc.). Examples: Salesforce.CreateContact, HubSpot, Airtable"""

    IDENTITY = "identity"
    """Manage authentication, users, or permissions. Examples: Okta.CreateUser, Auth0, AWS IAM"""

    # === Operations ===
    MONITORING = "monitoring"
    """Observe system health or manage incidents. Examples: Datadog.CreateMonitor, PagerDuty, CloudWatch"""

    DEPLOYMENT = "deployment"
    """Release software or provision infrastructure. Examples: Vercel.Deploy, GitHub Actions, Terraform"""

    # === Physical ===
    SENSING = "sensing"
    """Capture data from the physical environment. Examples: Cameras, temperature sensors, screenshots"""

    ACTUATION = "actuation"
    """Cause physical effects or control interfaces. Examples: Robot arms, smart plugs, browser clicks"""

    LOCATION = "location"
    """Work with position or geospatial data. Examples: GPS, Google Maps, geocoding"""

    # === AI ===
    REASONING = "reasoning"
    """AI planning, decision-making, or autonomous agents. Examples: AI agents, planners, decision engines"""


class SystemType(str, Enum):
    """
    The type of system this tool interfaces with.

    Provides orthogonal signal that disambiguates tools with the same domain.
    For example, "read temperature" could match IoT sensors (HARDWARE) or
    web weather scrapers (WEB) - SystemType helps distinguish them.
    """

    SAAS_API = "saas_api"
    """Third-party SaaS platforms accessed via their APIs. Examples: Slack, Salesforce, GitHub, Stripe"""

    DATABASE = "database"
    """Data storage systems with query interfaces. Examples: PostgreSQL, MongoDB, Redis, Elasticsearch"""

    FILE_SYSTEM = "file_system"
    """File storage systems (local or cloud). Examples: Local disk, S3, Google Drive, Dropbox"""

    WEB = "web"
    """Web pages, browsers, or web scraping. Examples: Firecrawl, Playwright, web search"""

    OPERATING_SYSTEM = "operating_system"
    """OS-level operations including browser/computer automation. Examples: Shell commands, browser automation, file operations"""

    HARDWARE = "hardware"
    """IoT devices, sensors, robotics, or physical devices. Examples: Thermostats, robot arms, cameras, smart plugs"""

    AI_MODEL = "ai_model"
    """LLM or ML model invocation. Examples: Claude, GPT, embeddings models, image generators"""

    AI_AGENT = "ai_agent"
    """Autonomous AI agents that perform multi-step tasks. Examples: Research agents, planning agents"""

    CUSTOM_API = "custom_api"
    """Customer's internal or private APIs. Examples: Internal microservices, proprietary systems"""

    SELF_CONTAINED = "self_contained"
    """No external system — pure computation, fully self-contained. Examples: Math.Add, JSON.Parse, string formatting"""


class Verb(str, Enum):
    """
    The action(s) the tool performs.

    Can be used for policy decisions and to infer behavior flags.
    """

    READ = "read"
    """
    Retrieves, queries, or observes data without modifying system state.

    When to use: Any operation that only returns information - fetching records,
    searching, listing resources, watching/subscribing to events, validating data,
    dry-run previews. Tools with only READ verb should have read_only=True.
    """

    CREATE = "create"
    """
    Brings a new resource or record into existence.

    When to use: Inserting new records, uploading files, provisioning resources,
    scheduling jobs, posting messages, instantiating new entities.
    The resource did not exist before the operation.
    """

    UPDATE = "update"
    """
    Modifies an existing resource's state or content.

    When to use: Editing records, changing configuration, renaming, archiving/restoring,
    patching, associating/disassociating resources (linking), changing lifecycle state
    (start/stop/pause). The resource identity persists after the operation.
    """

    DELETE = "delete"
    """
    Removes a resource or record from the system.

    When to use: Permanent deletion, soft-delete where resource becomes inaccessible,
    canceling queued jobs, unsubscribing, removing files. Use when the resource is
    no longer retrievable through normal operations. Tools with DELETE should have
    destructive=True.
    """

    EXECUTE = "execute"
    """
    Performs an action or runs a process with side effects beyond data manipulation.

    When to use: Running code, invoking functions, triggering webhooks, sending messages,
    calling external APIs that "do something," browser automation, shell commands,
    AI model inference. Use when the operation has effects but isn't fundamentally
    about CRUD on a resource.
    """

    AUTHORIZE = "authorize"
    """
    Grants, revokes, or modifies access rights and permissions.

    When to use: Role assignment, permission changes, sharing resources, generating
    access tokens, API key management, OAuth consent, modifying ACLs. These are
    security-critical operations that change who can do what.
    """


_READ_ONLY_VERBS = {Verb.READ}
_MUTATING_VERBS = {Verb.CREATE, Verb.UPDATE, Verb.DELETE, Verb.EXECUTE, Verb.AUTHORIZE}
_CLOSED_WORLD_SYSTEM_TYPES = {SystemType.SELF_CONTAINED}


class Classification(BaseModel):
    """
    What the tool is FOR and what it connects to.

    Used for tool discovery and search boosting.

    Example:
        Classification(
            domains=[Domain.CODE, Domain.SEARCH],  # GitHub.SearchCode spans both
            system_types=[SystemType.SAAS_API],
        )
    """

    domains: list[Domain] | None = None
    """The capability areas this tool operates in. Multi-select."""

    system_types: list[SystemType] | None = None
    """The types of systems this tool interfaces with. Multi-select."""

    model_config = ConfigDict(extra="forbid")


class Behavior(BaseModel):
    """
    What effects does the tool have? Arcade's data model for tool behavior.

    When using MCP, Behavior is project to MCP annotations.
    - read_only -> readOnlyHint
    - destructive -> destructiveHint
    - idempotent -> idempotentHint
    - open_world -> openWorldHint

    Verbs describe actions and can be used for policy decisions (e.g., "require
    human approval for DELETE tools").

    Example:
        Behavior(
            verbs=[Verb.DELETE],
            read_only=False,
            destructive=True,   # DELETE should be destructive
            idempotent=True,    # Deleting twice has same effect
            open_world=True,    # Interacts with external system
        )
    """

    verbs: list[Verb] | None = None
    """The actions the tool performs. Multi-select for compound operations."""

    read_only: bool | None = None
    """Tool only reads data, no mutations. Maps to MCP readOnlyHint."""

    destructive: bool | None = None
    """Tool can cause irreversible data loss. Maps to MCP destructiveHint."""

    idempotent: bool | None = None
    """Repeated calls with same input have no additional effect. Maps to MCP idempotentHint."""

    open_world: bool | None = None
    """Tool interacts with external systems (not purely in-process). Maps to MCP openWorldHint."""

    model_config = ConfigDict(extra="forbid")


class ToolMetadata(BaseModel):
    """
    Container for metadata about a tool.

    - classification: What is this tool for? What does it connect to? (for discovery/boosting)
    - behavior: What effects does it have? (for policy, filtering, MCP annotations)
    - extras: Arbitrary key/values for custom logic (e.g., IDP routing, feature flags)

    Strict Mode Validation:
        By default (strict=True), the constructor validates for logical contradictions:
        - Mutating verbs + read_only=True -> Error
        - DELETE verb + destructive=False -> Error
        - SELF_CONTAINED only + open_world=True -> Error
        - Remote system types + open_world=False -> Error

        Set strict=False to bypass validation for valid edge cases (e.g., a "read"
        tool that increments a view count as a side effect).

    Example:
        ToolMetadata(
            classification=Classification(
                domains=[Domain.MESSAGING],
                system_types=[SystemType.SAAS_API],
            ),
            behavior=Behavior(
                verbs=[Verb.EXECUTE],
                read_only=False,
                destructive=False,
                idempotent=False,
                open_world=True,
            ),
            extras={"idp": "entraID", "requires_mfa": True},
        )
    """

    classification: Classification | None = None
    """What the tool is for and what it connects to."""

    behavior: Behavior | None = None
    """What effects the tool has."""

    extras: dict[str, Any] | None = None
    """Arbitrary key/values for custom logic."""

    strict: bool = Field(default=True, exclude=True)
    """Enable validation for logical contradictions. Set False for edge cases.
    Excluded from serialization - this is a validation-time config flag, not tool metadata."""

    model_config = ConfigDict(extra="forbid")

    def validate_for_tool(self) -> None:
        """
        Validate consistency between behavior and classification.

        Called by the catalog when creating a tool definition

        Raises:
            ToolDefinitionError: If strict=True and validation fails
        """
        if not self.strict:
            return

        behavior = self.behavior
        classification = self.classification

        if behavior:
            verbs = set(behavior.verbs or [])

            # Rule 1: Mutating verbs + read_only=True is contradictory
            mutating_verbs = verbs & _MUTATING_VERBS
            if mutating_verbs and behavior.read_only is True:
                raise ToolDefinitionError(
                    f"Tool has the mutating verb(s): '{', '.join([verb.value.upper() for verb in mutating_verbs])}' "
                    f"in its behavior metadata, but is marked read_only=True. Fix the contradiction, or "
                    "set strict=False in the tool's ToolMetadata to bypass this validation for legitimate edge cases."
                )

            # Rule 2: DELETE verb should have destructive=True
            if Verb.DELETE in verbs and behavior.destructive is False:
                raise ToolDefinitionError(
                    f"Tool has the '{Verb.DELETE.value.upper()}' verb in its behavior metadata, "
                    f"but is not marked destructive=True. Fix the contradiction, or "
                    "set strict=False in the tool's ToolMetadata to bypass this validation for legitimate edge cases."
                )

        if classification and behavior:
            system_types = set(classification.system_types or [])

            # Rule 3: Closed-world (SELF_CONTAINED only) + open_world=True is contradictory
            closed_world_types = system_types & _CLOSED_WORLD_SYSTEM_TYPES
            if (
                system_types
                and system_types <= _CLOSED_WORLD_SYSTEM_TYPES
                and behavior.open_world is True
            ):
                raise ToolDefinitionError(
                    "Tool has the closed-world system type(s): "
                    f"'{', '.join([st.value.upper() for st in closed_world_types])}' "
                    "in its classification metadata, but is marked open_world=True. Fix the contradiction, or "
                    "set strict=False in the tool's ToolMetadata to bypass this validation for legitimate edge cases."
                )

            # Rule 4: Remote system types should have open_world=True
            remote_types = system_types - _CLOSED_WORLD_SYSTEM_TYPES
            if (
                system_types
                and not system_types <= _CLOSED_WORLD_SYSTEM_TYPES
                and behavior.open_world is False
            ):
                raise ToolDefinitionError(
                    "Tool has the remote system type(s): "
                    f"'{', '.join([st.value.upper() for st in remote_types])}' "
                    "in its classification metadata, but is marked open_world=False. Fix the contradiction, or "
                    "set strict=False in the tool's ToolMetadata to bypass this validation for legitimate edge cases."
                )
