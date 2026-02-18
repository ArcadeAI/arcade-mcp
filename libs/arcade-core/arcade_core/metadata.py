"""
Tool Metadata

Defines the metadata model for Arcade tools. This module provides three layers:

- Classification: What type of service the tool interfaces with (ServiceDomain).
  Used for tool discovery and search boosting.

- Behavior: What effects the tool has (operations, MCP-aligned flags).
  MCP Annotations are computed from this.
  Commonly used for policy decisions (HITL gates, retry logic, etc.)

- Extras: Arbitrary key/values for custom logic (IDP routing, feature flags, etc.)
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidatorFunctionWrapHandler, field_validator

from arcade_core.errors import ToolDefinitionError


class ServiceDomain(str, Enum):
    """
    The type of service a tool interfaces with.

    Classifies the target service whose data or functionality the tool provides
    access to -- not the infrastructure used to access it.

    Assignment is based on how the service self-identifies and is broadly
    recognized in its market. For tools that interact with no external service
    (open_world=False), ServiceDomain is None..
    """

    PROJECT_MANAGEMENT = "project_management"
    """Project tracking, issue management, and work item software."""

    CRM = "crm"
    """Customer relationship management - contacts, deals, pipelines, sales activities."""

    EMAIL = "email"
    """Email services for sending, receiving, and managing messages."""

    CALENDAR = "calendar"
    """Calendar and scheduling services."""

    MESSAGING = "messaging"
    """Real-time team and business messaging platforms."""

    DOCUMENTS = "documents"
    """Document editing, wikis, and knowledge base platforms."""

    CLOUD_STORAGE = "cloud_storage"
    """Cloud file storage and sharing services."""

    SPREADSHEETS = "spreadsheets"
    """Spreadsheet and tabular data software."""

    PRESENTATIONS = "presentations"
    """Presentation and slideshow software."""

    DESIGN = "design"
    """UI/UX design and prototyping tools."""

    SOURCE_CODE = "source_code"
    """Source code management, version control, and code review."""

    PAYMENTS = "payments"
    """Payment processing, invoicing, and billing."""

    SOCIAL_MEDIA = "social_media"
    """Platforms where users publish content to a public audience through a social feed."""

    VIDEO_HOSTING = "video_hosting"
    """Video hosting, streaming, and distribution platforms."""

    MUSIC_STREAMING = "music_streaming"
    """Music streaming and playback platforms."""

    CUSTOMER_SUPPORT = "customer_support"
    """Help desk, ticketing, and customer service software."""

    ECOMMERCE = "ecommerce"
    """Online shopping, product catalogs, and retail platforms."""

    INCIDENT_MANAGEMENT = "incident_management"
    """Incident response, on-call management, and operational alerting."""

    WEB_SCRAPING = "web_scraping"
    """Web data extraction and crawling services."""

    CODE_SANDBOX = "code_sandbox"
    """Cloud code execution and sandboxed runtime environments."""

    VIDEO_CONFERENCING = "video_conferencing"
    """Video meeting and conferencing platforms."""

    GEOSPATIAL = "geospatial"
    """Maps, navigation, directions, and geocoding services."""

    FINANCIAL_DATA = "financial_data"
    """Financial market data and stock information services."""

    TRAVEL = "travel"
    """Travel search, flight and hotel booking platforms."""


class Operation(str, Enum):
    """
    Classifies the tool's effect on resources in the target system.

    The concrete values represent the four fundamental resource lifecycle
    operations (read, create, update, delete). OPAQUE indicates the effect
    cannot be determined from the tool's definition because it depends
    on runtime inputs such as "ExecuteBashCommand(command="...")".

    Can be used for policy decisions (e.g., "require human approval for DELETE tools").
    """

    READ = "read"
    """
    Observes resources without changing state in the target system.

    When to use: Any operation that only returns information -- fetching records,
    searching, listing resources, watching/subscribing to events, validating data,
    dry-run previews. Tools with only READ should have read_only=True.
    """

    CREATE = "create"
    """
    Brings a new resource or record into existence.

    When to use: Inserting new records, uploading files, provisioning resources,
    scheduling jobs, posting messages, sending emails, instantiating new entities.
    The resource did not exist before the operation.
    """

    UPDATE = "update"
    """
    Modifies an existing resource's state, permissions, metadata, or content.

    When to use: Editing records, changing configuration, renaming, archiving/restoring,
    patching, associating/disassociating resources (linking), changing lifecycle state
    (start/stop/pause), sharing resources, modifying access permissions.
    The resource identity persists after the operation.
    """

    DELETE = "delete"
    """
    Removes a resource or record from the system.

    When to use: Permanent deletion, soft-delete where resource becomes inaccessible,
    canceling queued jobs, unsubscribing, removing files. Use when the resource is
    no longer retrievable through normal operations. Tools with DELETE should have
    destructive=True.
    """

    OPAQUE = "opaque"
    """
    Effect cannot be determined from the tool's definition because behavior
    depends entirely on runtime inputs.

    When to use: Tools like Bash.ExecuteCommand(command="...") or E2b.RunCode(code="...")
    where the actual operation is unknowable at definition time. OPAQUE signals to
    policy engines that this tool's effects are indeterminate and should be treated
    with caution.
    """


# Operation categories for validation
_READ_ONLY_OPERATIONS = {Operation.READ}
_MUTATING_OPERATIONS = {Operation.CREATE, Operation.UPDATE, Operation.DELETE}
_INDETERMINATE_OPERATIONS = {Operation.OPAQUE}


class Classification(BaseModel):
    """
    What type of service does this tool interface with?

    Used for tool discovery and search boosting.

    Examples:
        Classification(service_domains=[ServiceDomain.EMAIL])
        Classification(service_domains=[ServiceDomain.CLOUD_STORAGE, ServiceDomain.DOCUMENTS])
    """

    service_domains: list[ServiceDomain] | None = None
    """The service category/categories the tool's backing service belongs to. Multi-select."""

    model_config = ConfigDict(extra="forbid")


class Behavior(BaseModel):
    """
    What effects does the tool have? Arcade's data model for tool behavior.

    When using MCP, Behavior is projected to MCP annotations:
    - read_only -> readOnlyHint
    - destructive -> destructiveHint
    - idempotent -> idempotentHint
    - open_world -> openWorldHint

    Operations classify the tool's effect on resources and can be used for
    policy decisions (e.g., "require human approval for DELETE tools").

    Example:
        Behavior(
            operations=[Operation.DELETE],
            read_only=False,
            destructive=True,   # DELETE should be destructive
            idempotent=True,    # Deleting twice has same effect
            open_world=True,    # Interacts with external system
        )
    """

    operations: list[Operation] | None = None
    """The tool's effect on resources in the target system. Multi-select for compound operations."""

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

    - classification: What type of service does this tool interface with? (for discovery/boosting)
    - behavior: What effects does it have? (for policy, filtering, MCP annotations)
    - extras: Arbitrary key/values for custom logic (e.g., IDP routing, feature flags)

    Strict Mode Validation:
        By default (strict=True), the constructor validates for logical contradictions:
        - Mutating operations + read_only=True -> Error
        - OPAQUE operation + read_only=True -> Error
        - DELETE operation + destructive=False -> Error
        - ServiceDomain present + open_world=False -> Error

        Set strict=False to bypass validation for valid edge cases (e.g., a "read"
        tool that increments a view count as a side effect).

    Example:
        ToolMetadata(
            classification=Classification(
                service_domains=[ServiceDomain.EMAIL],
            ),
            behavior=Behavior(
                operations=[Operation.CREATE],
                read_only=False,
                destructive=False,
                idempotent=False,
                open_world=True,
            ),
            extras={"idp": "entraID", "requires_mfa": True},
        )
    """

    classification: Classification | None = None
    """What type of service the tool interfaces with."""

    behavior: Behavior | None = None
    """What effects the tool has."""

    extras: dict[str, Any] | None = None
    """Arbitrary key/values for custom logic. Must contain only JSON-native types
    (str, int, float, bool, None, dict with string keys, list) at all depths."""

    @field_validator("extras", mode="wrap")
    @classmethod
    def _validate_extras_top_level_keys(
        cls, v: dict[str, Any] | None, handler: ValidatorFunctionWrapHandler
    ) -> dict[str, Any] | None:
        """Intercept Pydantic's type validation to give a clear error for
        non-string top-level keys. Full recursive JSON-safety validation
        (nested keys + value types) is deferred to validate_for_tool()
        which is called when the tool definition is created for the catalog."""
        if v is not None and isinstance(v, dict):
            bad_keys = {k: type(k).__name__ for k in v if not isinstance(k, str)}
            if bad_keys:
                examples = ", ".join(f"{k!r} ({t})" for k, t in bad_keys.items())
                raise ToolDefinitionError(
                    f"All keys in ToolMetadata.extras must be strings. "
                    f"Found non-string key(s): {examples}. "
                )
        result: dict[str, Any] | None = handler(v)
        return result

    strict: bool = Field(default=True, exclude=True)
    """Enable validation for logical contradictions. Set False for edge cases.
    Excluded from serialization - this is a validation-time config flag, not tool metadata."""

    model_config = ConfigDict(extra="forbid")

    def validate_for_tool(self) -> None:
        """
        Validate metadata consistency and JSON-safety of extras.

        Called by the catalog when creating a tool definition.

        Raises:
            ToolDefinitionError: If strict=True and validation fails
        """
        # JSON-safety check on extras
        if self.extras is not None:
            errors = _find_json_violations(self.extras, "extras")
            if errors:
                formatted = "; ".join(errors)
                raise ToolDefinitionError(
                    f"ToolMetadata.extras must contain only JSON-safe "
                    f"types (str, int, float, bool, None, dict, list). "
                    f"Found violations: {formatted}. "
                    f"All dict keys must be strings, and all values must be "
                    f"JSON-native types."
                )

        if not self.strict:
            return

        behavior = self.behavior
        classification = self.classification

        if behavior:
            operations = set(behavior.operations or [])

            # Rule 1: Mutating operations + read_only=True is contradictory
            mutating_ops = operations & _MUTATING_OPERATIONS
            if mutating_ops and behavior.read_only is True:
                raise ToolDefinitionError(
                    f"Tool has the mutating operation(s): "
                    f"'{', '.join([op.value.upper() for op in mutating_ops])}' "
                    f"in its behavior metadata, but is marked read_only=True. "
                    "Fix the contradiction, or set strict=False to bypass."
                )

            # Rule 2: OPAQUE + read_only=True is contradictory
            if Operation.OPAQUE in operations and behavior.read_only is True:
                raise ToolDefinitionError(
                    "Tool has OPAQUE operation but is marked read_only=True. "
                    "Cannot guarantee read-only when the operation is indeterminate. "
                    "Fix the contradiction, or set strict=False to bypass."
                )

            # Rule 3: DELETE should have destructive=True
            if Operation.DELETE in operations and behavior.destructive is False:
                raise ToolDefinitionError(
                    f"Tool has the '{Operation.DELETE.value.upper()}' operation "
                    "but is not marked destructive=True. "
                    "Fix the contradiction, or set strict=False to bypass."
                )

        if classification and behavior:
            service_domains = classification.service_domains or []

            # Rule 4: ServiceDomain present implies open_world=True
            if len(service_domains) > 0 and behavior.open_world is False:
                raise ToolDefinitionError(
                    "Tool has a ServiceDomain (implying an external service) "
                    "but is marked open_world=False. "
                    "Fix the contradiction, or set strict=False to bypass."
                )


def _find_json_violations(obj: Any, path: str) -> list[str]:
    """Walk a nested structure and return human-readable descriptions of
    any non-JSON-native keys or values.

    JSON-native: str, int, float, bool, None, dict (string keys only), list.
    """
    errors: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_path = f"{path}[{k!r}]"
            if not isinstance(k, str):
                errors.append(
                    f"{key_path} has a non-string key of type {type(k).__name__} — "
                    f"all dict keys must be strings"
                )
            errors.extend(_find_json_violations(v, key_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            errors.extend(_find_json_violations(item, f"{path}[{i}]"))
    # json primitive types
    elif not isinstance(obj, (str, int, float, bool, type(None))):
        errors.append(
            f"{path} has a non-JSON-safe value of type {type(obj).__name__} (got {obj!r})"
        )
    return errors
