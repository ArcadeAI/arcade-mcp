from starlette.requests import Request

from arcade.tool.catalog import ToolCatalog


def get_catalog(request: Request) -> ToolCatalog:
    # TODO figure out why this says return type is Any
    return request.app.state.catalog  # type: ignore[no-any-return]
