from arcade_tdk.errors import ToolExecutionError


class HubspotToolExecutionError(ToolExecutionError):
    pass


class NotFoundError(HubspotToolExecutionError):
    pass
