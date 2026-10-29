"""A stand-in MCP endpoint at /mcp as a bare ASGI app, for ``uvicorn asgi_app:app --workers 2``."""

from typing import Any

from fake_responses import answer


async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    if scope["path"] != "/mcp" or scope["method"] != "POST":
        status, headers, payload = 404, {}, b""
    else:
        status, headers, payload = answer(body)

    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(name.lower().encode(), value.encode()) for name, value in headers.items()],
    })
    await send({"type": "http.response.body", "body": payload})
