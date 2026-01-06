from enum import Enum

from pydantic import BaseModel, ConfigDict


class Verb(str, Enum):
    """
    Classifies the primary action performed by the tool.
    """

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    TRANSFER = "transfer"
    MANAGE = "manage"
    CONTROL = "control"
    AUTHORIZE = "authorize"
    DENY = "deny"
    ASSOCIATE = "associate"
    DISASSOCIATE = "disassociate"
    MONITOR = "monitor"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


class Scope(str, Enum):
    """
    Defines where the authoritative state lives.
    """

    INTERNAL = "internal"
    # State is owned and controlled by the LLM's host system

    EXTERNAL = "external"
    # State is owned by a third-party system or environment

    HYBRID = "hybrid"
    # Tool bridges internal and external state-spaces


class Domain(str, Enum):
    """
    Classifies the primary state-space a tool exposes or mutates.
    """

    SYMBOLIC = "symbolic"
    # Unstructured representations: text, images, audio, video, code

    STRUCTURED_DATA = "structured_data"
    # Typed records, tables, schemas, metrics

    MEMORY = "memory"
    # Persistence, recall, embeddings, logs

    TIME = "time"
    # Temporal state: schedules, timers, ordering, deadlines

    IDENTITY = "identity"
    # Actors, principals, credentials, profiles

    COMMUNICATION = "communication"
    # Directed information exchange between actors

    SEARCH = "search"
    # Discovery over unknown or partially known spaces

    INFERENCE = "inference"
    # Derived knowledge: analytics, classification, prediction

    PLANNING = "planning"
    # Sequencing and goal decomposition

    EXECUTION = "execution"
    # Triggering code paths, workflows, automations

    CONFIGURATION = "configuration"
    # Modifying system behavior via settings or policies

    ACCESS_CONTROL = "access_control"
    # Permissions, authorization, enforcement

    TRANSACTION = "transaction"
    # Irreversible, accountable state changes

    PHYSICAL = "physical"
    # Sensors, actuators, robots, IoT

    SIMULATION = "simulation"
    # Counterfactual or sandboxed worlds


# class Domain(str, Enum):
#     """
#     High-level functional domain the tool belongs to.
#     Tools can belong to multiple domains.

#     Litmus test:
#     If it can be applied uniformly to every domain, it is not itself a domain.
#     """

#     COMMUNICATION = "communication"  # Internal/external communication
#     CONTENT = "content"  # Content management, publishing
#     ECOMMERCE = "ecommerce"  # E-commerce, retail, inventory
#     PRODUCTIVITY = "productivity"
#     CALENDAR = "calendar"
#     STORAGE = "storage"
#     RESEARCH = "research"
#     FINANCE = "finance"  # Finance, accounting, billing, payments
#     SALES = "sales"  # Sales operations, CRM, leads, opportunities, deals
#     MARKETING = "marketing"  # Marketing campaigns, email, content, analytics
#     ENGINEERING = "engineering"  # Software development, DevOps, infrastructure
#     IT = "it"  # IT operations, infrastructure, systems
#     DESIGN = "design"  # Design, UX, creative
#     SUPPORT = "support"  # Customer support, helpdesk, ticketing
#     PRODUCT = "product"  # Product management, roadmaps, features
#     HR = "hr"  # Human resources, recruiting, onboarding
#     LEGAL = "legal"  # Legal, compliance, contracts
#     SECURITY = "security"  # Security, access control, compliance
#     ANALYTICS = "analytics"  # Data analytics, reporting, insights
#     OPERATIONS = "operations"  # Business operations, administration
#     OTHER = "other"


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
    (one or more Domains) + (one or more Verbs) + (one Scope)
    """

    verb: Verb | None = None  # Single: What action (CREATE, READ, etc.)
    scope: Scope | None = None  # Single: System boundary (INTERNAL, EXTERNAL, HYBRID)
    domains: list[Domain] | None = None  # Multiple: Functional areas (can span multiple)

    model_config = ConfigDict(extra="allow")
