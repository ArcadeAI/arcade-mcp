from arcade.sdk.errors import ToolExecutionError


class HubspotToolExecutionError(ToolExecutionError):
    pass


class NotFoundError(HubspotToolExecutionError):
    pass
