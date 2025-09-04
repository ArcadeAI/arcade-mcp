from arcade_core.errors import ToolDefinitionError, ToolRuntimeError


class WrapperDefinitionError(ToolDefinitionError):
    """
    Raised when there is an error in the definition of a wrapper tool.
    """


class InvalidObjectVersionError(WrapperDefinitionError):
    """
    Raised when there is an error in the version of an object.
    """

    def __init__(self, version: str, object_name: str):
        super().__init__(f"Invalid version: '{version}' in {object_name} object.")


class WrapperToolRuntimeError(ToolRuntimeError):
    """
    Raised when there is an error in the execution of a wrapper tool.
    """


class WrapperToolExecutionError(WrapperToolRuntimeError):
    """
    Raised when there is an error in the execution of a wrapper tool.
    """
