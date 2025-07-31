import traceback
from typing import Any, Literal

# TODO: break out into separate files
# TODO: determine which errors should be abstract. (can't break backwards compatibility)
# TODO: should classes help build up the message/developer_message?
# TODO: remove "extra" entirely?


class ToolkitError(Exception):
    """
    Base class for all Arcade errors.

    Common (not enforced) attributes expected from subclasses:
      origin      : Literal['TOOL', 'UPSTREAM']
      retryable   : bool
      code        : str                # machine-readable subtype
      status_code : int | None         # HTTP-ish status when relevant
      extra       : dict[str, Any]     # arbitrary structured metadata
    """


class ToolkitLoadError(ToolkitError):
    """
    Raised while importing / loading a toolkit package
    (e.g. missing dependency, SyntaxError in module top-level code).
    """

    origin = "TOOL"
    retryable = False
    code = "LOAD_FAILED"


class ToolError(ToolkitError):
    """Any error related to an Arcade tool."""


# ------  definition-time errors (tool developer's responsibility) ------
class ToolDefinitionError(ToolError):
    """
    Raised when there is an error in the definition/signature of a tool.

    This is raised at the time of tool load/registration (when building the schema for the tool)
    """


class ToolInputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's input parameter."""

    origin = "TOOL"
    retryable = False
    code = "BAD_INPUT_SCHEMA"


class ToolOutputSchemaError(ToolDefinitionError):
    """Raised when there is an error in the schema of a tool's output parameter."""

    origin = "TOOL"
    retryable = False
    code = "BAD_OUTPUT_SCHEMA"


# ------  runtime errors ------


class ToolRuntimeError(
    ToolError, RuntimeError
):  # TODO: does it matter if this is a subclass of RuntimeError?
    """Any failure starting from when the tool call begins until the tool call returns."""

    origin: Literal["TOOL", "UPSTREAM"]
    retryable: bool
    code: str  # the semantic code of the error
    status_code: int | None = None  # the HTTP status code of the error
    extra: dict[str, Any]

    def __init__(
        self,
        message: str,
        *,
        developer_message: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.developer_message = developer_message
        self.extra = extra or {}

    def traceback_info(self) -> str | None:
        if self.__cause__:
            return "\n".join(traceback.format_exception(self.__cause__))
        return None

    # wire-format helper
    def to_payload(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "developer_message": self.developer_message,
            "origin": self.origin,
            "retryable": self.retryable,
            "code": self.code,
            "status_code": self.status_code,
            **self.extra,
        }


# 1. ------  serialization errors ------
class ToolSerializationError(ToolRuntimeError):  # TODO: probably make this abstract
    """Raised when there is an error serializing/marshalling the tool call arguments or return value."""

    origin = "TOOL"
    retryable = False


class ToolInputError(ToolSerializationError):
    """
    Raised when there is an error parsing a tool call argument.
    """

    code = "BAD_INPUT_VALUE"


class ToolOutputError(ToolSerializationError):
    """
    Raised when there is an error serializing a tool call return value.
    """

    code = "BAD_OUTPUT_VALUE"


# 2. ------  tool-body errors ------
class ToolExecutionError(
    ToolRuntimeError
):  # TODO: I'd love to make this abstract, but can't break backwards compatibility
    """
    Raised when there is an error executing a tool.
    """

    origin = "TOOL"


class RetryableToolError(ToolExecutionError):
    """
    Raised when a tool execution error is retryable.
    """

    retryable = True
    code = "TOOL_RETRY"

    def __init__(
        self,
        message: str,
        developer_message: str | None = None,
        additional_prompt_content: str | None = None,
        retry_after_ms: int | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.additional_prompt_content = additional_prompt_content
        self.retry_after_ms = retry_after_ms


class NonRetryableToolError(ToolExecutionError):
    """
    Raised when there is an error executing a tool.
    """

    retryable = False
    code = "BUG"

    def __init__(
        self,
        message: str,
        status_code: int,
        developer_message: str | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code


# 3. ------  upstream errors in tool body------
class UpstreamError(ToolRuntimeError):  # TODO: probably make this abstract
    """Parent error for all failures from the upstream provider."""

    origin = "UPSTREAM"


class UpstreamBadRequestError(UpstreamError):
    """Raised when an upstream provider returns a bad request error."""

    retryable = False
    code = "BAD_REQUEST"
    status_code = 400


class UpstreamAuthError(UpstreamError):
    """
    Raised when an upstream provider returns an authentication or authorization error.

    This covers both missing/invalid credentials (401) and insufficient permissions (403).
    """

    retryable = False
    code = "AUTH_ERROR"

    def __init__(
        self,
        message: str,
        status_code: int,  # must be 401 or 403
        *,
        developer_message: str | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code


class UpstreamNotFoundError(UpstreamError):
    """Raised when an upstream provider returns a not found error."""

    retryable = False
    code = "NOT_FOUND"
    status_code = 404


class UpstreamValidationError(UpstreamError):
    """Raised when upstream provider rejects request due to validation errors."""

    retryable = False
    code = "VALIDATION_ERROR"
    status_code = 422


class UpstreamRateLimitError(UpstreamError):
    """
    Raised when an upstream provider is rate limiting a request in a tool.
    """

    retryable = True
    code = "RATE_LIMIT"
    status_code = 429

    def __init__(
        self,
        retry_after_ms: int,
        message: str,
        *,
        developer_message: str | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.retry_after_ms = retry_after_ms


class UpstreamServerError(UpstreamError):
    """Raised when an upstream provider returns a server error (5xx)."""

    retryable = True
    code = "SERVER_ERROR"

    def __init__(
        self,
        message: str,
        status_code: int,  # must be 5xx
        *,
        developer_message: str | None = None,
    ):
        super().__init__(message, developer_message=developer_message)
        self.status_code = status_code
