from enum import Enum

from pydantic import AnyUrl, BaseModel, Field

from arcade.core.schema import ToolAuthorizationContext, ToolCallOutput


class AuthProvider(str, Enum):
    """The supported authorization providers."""

    oauth2 = "oauth2"
    """OAuth 2.0 authorization"""

    google = "google"
    """Google authorization"""

    slack_user = "slack_user"
    """Slack (user token) authorization"""

    github_app = "github_app"
    """GitHub App authorization"""


class AuthRequest(BaseModel):
    """
    The requirements for authorization for a tool
    # TODO (Nate): Make a validator here
    """

    authority: AnyUrl | str | None = None
    """The URL of the OAuth 2.0 authorization server."""

    scope: list[str]
    """The scope(s) needed for authorization."""


class AuthStatus(str, Enum):
    """The status of an authorization request."""

    pending = "pending"
    failed = "failed"
    completed = "completed"


class AuthResponse(BaseModel):
    """Response from an authorization request."""

    auth_id: str = Field(alias="authorizationID")
    """The ID of the authorization request"""

    scopes: list[str]
    """The scope(s) requested in the authorization request"""

    # TODO: Use AnyUrl?
    auth_url: str | None = Field(None, alias="authorizationURL")
    """The URL for the authorization"""

    status: AuthStatus
    """Only completed implies presence of a token"""

    context: ToolAuthorizationContext | None = None


class ExecuteToolResponse(BaseModel):
    """Response from executing a tool."""

    invocation_id: str
    """The globally-unique ID for this tool invocation in the run."""

    duration: float
    """The duration of the tool invocation in milliseconds."""

    finished_at: str
    """The timestamp when the tool invocation finished."""

    success: bool
    """Whether the tool invocation was successful."""

    output: ToolCallOutput | None = None
    """The output of the tool invocation."""
