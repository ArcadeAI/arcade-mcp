from arcade_core.errors import ToolDefinitionError


class WrapperDefinitionError(ToolDefinitionError):
    """
    Raised when there is an error in the definition of a wrapper tool.
    """

    pass


class InvalidObjectVersionError(WrapperDefinitionError):
    """
    Raised when there is an error in the version of an object.
    """

    def __init__(self, version: str, object_name: str):
        super().__init__(f"Invalid version: '{version}' in {object_name} object.")
